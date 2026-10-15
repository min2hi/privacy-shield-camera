from __future__ import annotations

import time
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import cv2
import numpy as np

from app.core.frame_scheduler import FrameScheduler
from app.core.masking import Masker
from app.core.temporal_smoothing import TemporalSmoothing, calculate_iou
from app.utils.logging_config import get_logger

if TYPE_CHECKING:
    from app.utils.config_loader import ConfigLoader

logger = get_logger(__name__)


class PrivacyPipeline:
    config: ConfigLoader
    detector: Any
    face_rec_enabled: bool
    face_threshold: float
    face_recognizer: Any
    mask_owner_face: bool
    mask_strangers_face: bool
    scheduler: FrameScheduler
    smoothing: TemporalSmoothing
    masker: Masker
    fail_safe: bool
    last_time: float
    fps: float
    last_face_tracks: list[dict[str, Any]]
    _last_effective_classes: tuple[str, ...] | None

    def __init__(
        self,
        config_loader: ConfigLoader,
        detector: Any = None,
        face_recognizer: Any = None,
    ) -> None:
        self.config = config_loader
        
        # Đọc cấu hình
        model_path = str(self.config.resolve_path("model.path", "models/yolov8n.pt"))
        manifest_path = self.config.resolve_path("model.manifest_path")
        conf = self.config.get("model.confidence", 0.25)
        iou = self.config.get("model.iou", 0.45)
        img_size = self.config.get("model.image_size", 640)
        
        # Heavy runtime dependencies are lazy and injectable for deterministic tests.
        if detector is None:
            from app.core.detector import Detector

            detector = Detector(
                model_path=model_path,
                confidence=conf,
                iou=iou,
                image_size=img_size,
                manifest_path=manifest_path,
            )
        self.detector = detector
        
        # Khởi tạo FaceRecognizer (Nhận diện khuôn mặt nâng cao)
        self.face_rec_enabled = self.config.get("face_recognition.enabled", True)
        self.face_threshold = self.config.get("face_recognition.threshold", 1.1)
        face_model_dir = self.config.resolve_path("face_recognition.model_dir", "models")
        face_template = self.config.resolve_path(
            "face_recognition.template_path", "configs/registered_face.npy"
        )
        if face_recognizer is None:
            from app.core.face_recognizer import FaceRecognizer

            face_recognizer = FaceRecognizer(
                threshold=self.face_threshold,
                model_dir=face_model_dir,
                registered_face_path=face_template,
            )
        self.face_recognizer = face_recognizer
        
        # Biến trạng thái điều khiển từ GUI
        self.mask_owner_face = self.config.get("face_recognition.mask_owner", True)
        self.mask_strangers_face = self.config.get("face_recognition.mask_stranger", False)
        
        # Khởi tạo Frame Scheduler (Frame Skipping)
        skip_enabled = self.config.get("privacy.frame_skipping.enabled", True)
        skip_ratio = self.config.get("privacy.frame_skipping.skip_ratio", 2)
        self.scheduler = FrameScheduler(enabled=skip_enabled, skip_ratio=skip_ratio)
        
        # Khởi tạo Temporal Smoothing
        hold_frames = self.config.get("privacy.hold_frames", 5)
        self.smoothing = TemporalSmoothing(hold_frames=hold_frames)
        
        # Khởi tạo Masker (Privacy Risk Levels + Bbox Expansion)
        class_presets = self.config.get("model.class_mask_presets", {})
        default_mask = self.config.get("privacy.mask_mode", "mosaic")
        expand_ratio = self.config.get("privacy.expand_bbox_ratio", 0.15)
        self.masker = Masker(
            class_mask_presets=class_presets,
            default_mask_mode=default_mask,
            expand_ratio=expand_ratio
        )
        
        self.fail_safe = self.config.get("privacy.fail_safe", True)
        self.last_time = time.perf_counter()
        self.fps = 0.0
        self.last_face_tracks = []
        self._last_face_detections: list[dict[str, Any]] = []
        self._face_cache_valid: bool = False
        self._last_face_policy: tuple[bool, bool, bool] | None = None
        self._last_effective_classes = None

    def reset_tracking(self) -> None:
        """Reset state that must not cross camera/model/policy sessions."""
        self.scheduler.reset()
        self.smoothing.reset()
        self.last_face_tracks = []
        self._last_face_detections = []
        self._face_cache_valid = False
        self._last_face_policy = None

    @staticmethod
    def privacy_screen(
        frame: np.ndarray | None,
        reason: str = "SAFE MODE ACTIVE",
        *,
        fallback_size: tuple[int, int] = (480, 640),
    ) -> np.ndarray:
        """Create a fail-closed frame without retaining any source pixels."""
        if frame is not None:
            h, w = frame.shape[:2]
        else:
            h, w = fallback_size
        screen = np.zeros((h, w, 3), dtype=np.uint8)
        cv2.putText(
            screen,
            "PRIVACY SHIELD",
            (max(16, w // 16), max(40, h // 2 - 16)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 245, 160),
            2,
        )
        cv2.putText(
            screen,
            str(reason)[:80],
            (max(16, w // 16), min(h - 20, h // 2 + 24)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )
        return screen

    def detect_and_smooth(
        self, frame: np.ndarray, selected_classes: Sequence[str] | list[str] | None = None
    ) -> tuple[list[dict[str, Any]], list[str], float]:
        """
        Thực thi suy luận AI (YOLO + Card/QR + YuNet/MobileFaceNet) và làm mịn Temporal Smoothing.
        Trả về: (smoothed_detections, unsupported_classes, inference_latency_ms)
        """
        infer_start = time.perf_counter()

        requested_classes = list(selected_classes or [])
        supported_classes = self.detector.supported_class_names
        unsupported_classes = sorted(set(requested_classes) - supported_classes)
        effective_classes = [name for name in requested_classes if name in supported_classes]

        # Invalidate tracking cache khi danh sách class thay đổi
        if not hasattr(self, "_last_effective_classes"):
            self._last_effective_classes = None
        current_classes_key = tuple(sorted(effective_classes)) if effective_classes else None
        if current_classes_key != self._last_effective_classes:
            if self._last_effective_classes is not None:
                self.reset_tracking()
            self._last_effective_classes = current_classes_key

        # 1. Quyết định xem có chạy YOLO hay không (Frame Skipping)
        did_run_object_detect = self.scheduler.should_detect()
        pre_skip_counter = getattr(self.scheduler, "frame_counter", 0)
        if did_run_object_detect:
            detections = self.detector.detect(
                frame,
                selected_classes=effective_classes if requested_classes else None,
            )
            self.scheduler.update_detections(detections)
        else:
            detections = self.scheduler.get_last_detections()
            self.scheduler.skip_frame()

        # 2. Xử lý nhận diện khuôn mặt nâng cao (Interleaved Scheduling + Face Tracking)
        face_detections: list[dict[str, Any]] = []
        if self.face_rec_enabled:
            reg_embs = getattr(self.face_recognizer, "registered_embeddings", None)
            has_registered = bool(reg_embs and any(e is not None for e in reg_embs))
            face_policy = (
                has_registered,
                bool(self.mask_owner_face),
                bool(self.mask_strangers_face),
            )
            if getattr(self, "_last_face_policy", None) != face_policy:
                self._last_face_policy = face_policy
                self._face_cache_valid = False
                self._last_face_detections = []
                if hasattr(self, "smoothing") and hasattr(self.smoothing, "active_boxes"):
                    self.smoothing.active_boxes = [
                        b for b in self.smoothing.active_boxes if b.get("class_name") != "face"
                    ]

            # Chỉ chạy nhận diện khuôn mặt khi có ít nhất 1 quy tắc che mặt có hiệu lực
            need_face_pipeline = (has_registered and self.mask_owner_face) or self.mask_strangers_face
            if not need_face_pipeline:
                self.last_face_tracks = []
                self._last_face_detections = []
                self._face_cache_valid = True
            else:
                scheduler_active = bool(getattr(self.scheduler, "enabled", False)) and (
                    getattr(self.scheduler, "skip_ratio", 1) >= 2
                )
                face_cache_valid = getattr(self, "_face_cache_valid", False)

                # Xen kẽ: nếu frame này vừa chạy YOLO và đã có cache mặt hợp lệ -> dùng lại cache mặt;
                # chạy YuNet ở frame nghỉ của YOLO (pre_skip_counter == 1) để san phẳng thời gian frame.
                should_run_face_detect = (
                    not scheduler_active
                    or not face_cache_valid
                    or (not did_run_object_detect and pre_skip_counter == 1)
                )

                if not should_run_face_detect:
                    face_detections = list(getattr(self, "_last_face_detections", []))
                else:
                    faces = self.face_recognizer.detect_faces(frame)
                    current_face_tracks: list[dict[str, Any]] = []
                    used_track_indices: set[int] = set()
                    same_face_count = len(faces) == len(self.last_face_tracks)

                    for face in faces:
                        xmin, ymin, w, h = face["bbox"]
                        x2 = xmin + w
                        y2 = ymin + h
                        bbox = (xmin, ymin, x2, y2)

                        # 2.1 So sánh 1-1 với các khuôn mặt ở frame trước bằng IoU
                        best_match = None
                        best_match_idx = -1
                        best_iou = 0.0
                        if same_face_count:
                            for idx, track in enumerate(self.last_face_tracks):
                                if idx in used_track_indices:
                                    continue
                                iou = calculate_iou(bbox, track["bbox"])
                                if iou > best_iou:
                                    best_iou = iou
                                    best_match = track
                                    best_match_idx = idx

                        is_matched = False
                        dist = 999.0
                        verify_failed = False

                        # Chỉ giữ cache dài (10 chu kỳ) cho mặt đã xác nhận là Chủ sở hữu;
                        # với mặt chưa khớp (is_matched=False), xác thực lại sau mỗi 1 chu kỳ để nhận diện chủ nhân tức thì.
                        max_track_ttl = (
                            10 if (best_match is not None and best_match.get("is_matched")) else 1
                        )

                        if (
                            best_match is not None
                            and best_iou > 0.45
                            and best_match["frames_since_update"] < max_track_ttl
                            and not best_match.get("verify_failed", False)
                        ):
                            used_track_indices.add(best_match_idx)
                            is_matched = bool(best_match["is_matched"])
                            dist = float(best_match.get("dist", 999.0))
                            frames_since_update = best_match["frames_since_update"] + 1
                        else:
                            if best_match is not None and best_iou > 0.40:
                                used_track_indices.add(best_match_idx)
                            # Chỉ chạy MobileFaceNet khi đã đăng ký mặt mẫu và cần phân biệt chủ/lạ
                            if has_registered:
                                if hasattr(self.face_recognizer, "verify_face_region"):
                                    is_matched, dist, verify_failed = (
                                        self.face_recognizer.verify_face_region(frame, face)
                                    )
                                else:
                                    face_crop = frame[ymin:y2, xmin:x2]
                                    if face_crop.size == 0:
                                        verify_failed = True
                                    else:
                                        try:
                                            embedding = self.face_recognizer.extract_embedding(
                                                face_crop
                                            )
                                            if embedding is None:
                                                verify_failed = True
                                            else:
                                                is_matched, dist = (
                                                    self.face_recognizer.verify_face(embedding)
                                                )
                                        except Exception as exc:
                                            logger.warning(
                                                "Face verification error (fail-closed): %s", exc
                                            )
                                            verify_failed = True

                                # Làm mịn khoảng cách EMA + Hysteresis chống nhấp nháy cho track của Chủ sở hữu
                                if (
                                    not verify_failed
                                    and best_match is not None
                                    and best_iou > 0.40
                                ):
                                    prev_dist = float(best_match.get("dist", 999.0))
                                    if prev_dist < 500.0:
                                        dist = 0.40 * prev_dist + 0.60 * dist
                                    thresh = float(
                                        getattr(self.face_recognizer, "threshold", 1.15)
                                    )
                                    if best_match.get("is_matched", False) and dist < (
                                        thresh + 0.08
                                    ):
                                        is_matched = True
                                    elif dist < thresh:
                                        is_matched = True
                            frames_since_update = 0

                        current_face_tracks.append({
                            "bbox": bbox,
                            "is_matched": is_matched,
                            "dist": dist,
                            "verify_failed": verify_failed,
                            "frames_since_update": frames_since_update,
                        })

                    # 2.2 Khử nhập nhằng đa khuôn mặt: trong cùng 1 khung hình chỉ có tối đa 1 Chủ sở hữu
                    # (khuôn mặt có khoảng cách Euclidean nhỏ nhất đạt ngưỡng). Các khuôn mặt còn lại là Người lạ.
                    matched_indices = [
                        idx for idx, trk in enumerate(current_face_tracks) if trk["is_matched"]
                    ]
                    if len(matched_indices) > 1:
                        best_owner_idx = min(
                            matched_indices, key=lambda idx: current_face_tracks[idx]["dist"]
                        )
                        for idx in matched_indices:
                            if idx != best_owner_idx:
                                current_face_tracks[idx]["is_matched"] = False

                    # 2.3 Áp dụng quyết định che phủ chuẩn xác cho từng khuôn mặt
                    for track in current_face_tracks:
                        bbox = track["bbox"]
                        is_matched = track["is_matched"]
                        verify_failed = track["verify_failed"]
                        should_mask = False
                        mask_mode = "gaussian_blur"

                        if is_matched:
                            # Khuôn mặt khớp với Chủ sở hữu
                            if self.mask_owner_face:
                                should_mask = True
                                mask_mode = "gaussian_blur"
                        else:
                            # Khuôn mặt KHÔNG khớp Chủ sở hữu (Người lạ) hoặc lỗi trích xuất
                            if self.mask_strangers_face:
                                should_mask = True
                                mask_mode = "mosaic"
                            elif verify_failed and self.mask_owner_face and has_registered:
                                # Fail-Closed chỉ kích hoạt khi lỗi trích xuất/xác thực, KHÔNG che nhầm người lạ
                                should_mask = True
                                mask_mode = "gaussian_blur"

                        if should_mask:
                            face_detections.append({
                                "class_name": "face",
                                "bbox": bbox,
                                "confidence": 1.0,
                                "mask_mode": mask_mode,
                            })

                    self.last_face_tracks = current_face_tracks
                    self._last_face_detections = list(face_detections)
                    self._face_cache_valid = True

        # Hợp nhất các hộp phát hiện của YOLOv8 và các hộp che khuôn mặt
        all_detections = detections + face_detections

        # 3. Áp dụng Temporal Smoothing chống nhấp nháy
        smoothed_detections = self.smoothing.update(all_detections)
        infer_latency = (time.perf_counter() - infer_start) * 1000.0
        return smoothed_detections, unsupported_classes, infer_latency

    def render_masked_frame(
        self,
        frame: np.ndarray,
        smoothed_detections: list[dict[str, Any]],
        unsupported_classes: list[str],
        latency_ms: float,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Áp dụng mặt nạ che phủ siêu tốc (~0.3ms) lên frame hiện tại và tính toán FPS."""
        processed_frame = self.masker.apply_masks(frame, smoothed_detections)

        curr_time = time.perf_counter()
        time_diff = curr_time - self.last_time
        self.last_time = curr_time
        if time_diff > 0:
            instant_fps = 1.0 / time_diff
            self.fps = 0.85 * self.fps + 0.15 * instant_fps if self.fps > 0 else instant_fps

        metrics = {
            "fps": round(self.fps, 1),
            "latency_ms": round(latency_ms, 1),
            "detected_count": len(smoothed_detections),
            "detections": smoothed_detections,
            "unsupported_classes": unsupported_classes,
            "state": "protected",
        }
        return processed_frame, metrics

    def process_frame(
        self, frame: np.ndarray, selected_classes: Sequence[str] | list[str] | None = None
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """
        Xử lý chính trên mỗi frame webcam.
        Trả về: (processed_frame, metrics)
        """
        start_time = time.perf_counter()

        try:
            smoothed_detections, unsupported_classes, _ = self.detect_and_smooth(
                frame, selected_classes=selected_classes
            )
            processed_frame = self.masker.apply_masks(frame, smoothed_detections)
            latency = (time.perf_counter() - start_time) * 1000.0

            curr_time = time.perf_counter()
            time_diff = curr_time - self.last_time
            self.last_time = curr_time
            if time_diff > 0:
                instant_fps = 1.0 / time_diff
                self.fps = 0.9 * self.fps + 0.1 * instant_fps if self.fps > 0 else instant_fps

            metrics = {
                "fps": round(self.fps, 1),
                "latency_ms": round(latency, 1),
                "detected_count": len(smoothed_detections),
                "detections": smoothed_detections,
                "unsupported_classes": unsupported_classes,
                "state": "protected",
            }
            return processed_frame, metrics

        except Exception as e:
            logger.error("PrivacyPipeline error: %s", e, exc_info=True)

            # Cơ chế Fail-safe: Nếu bật, xuất màn hình đen kèm thông báo thay vì video thô
            if self.fail_safe:
                black_frame = self.privacy_screen(frame, "PIPELINE ERROR - SAFE MODE ACTIVE")
                metrics = {
                    "fps": 0.0,
                    "latency_ms": 0.0,
                    "detected_count": 0,
                    "detections": [],
                    "error": str(e),
                    "state": "error",
                }
                return black_frame, metrics
            else:
                # Nếu không bật fail-safe, ném biệt lệ ra ngoài
                raise e
