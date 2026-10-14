import time

import cv2
import numpy as np

from app.core.frame_scheduler import FrameScheduler
from app.core.masking import Masker
from app.core.temporal_smoothing import TemporalSmoothing, calculate_iou
from app.utils.console import safe_print


class PrivacyPipeline:
    def __init__(self, config_loader, detector=None, face_recognizer=None):
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

    def reset_tracking(self):
        """Reset state that must not cross camera/model/policy sessions."""
        self.scheduler.reset()
        self.smoothing.reset()
        self.last_face_tracks = []

    @staticmethod
    def privacy_screen(frame, reason="SAFE MODE ACTIVE", *, fallback_size=(480, 640)):
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

    def process_frame(self, frame, selected_classes=None):
        """
        Xử lý chính trên mỗi frame webcam.
        Trả về: (processed_frame, metrics)
        """
        start_time = time.perf_counter()
        
        try:
            requested_classes = list(selected_classes or [])
            supported_classes = self.detector.supported_class_names
            unsupported_classes = sorted(set(requested_classes) - supported_classes)
            effective_classes = [name for name in requested_classes if name in supported_classes]

            # Invalidate tracking cache khi danh sách class thay đổi
            if not hasattr(self, '_last_effective_classes'):
                self._last_effective_classes = None
            current_classes_key = tuple(sorted(effective_classes)) if effective_classes else None
            if current_classes_key != self._last_effective_classes:
                if self._last_effective_classes is not None:
                    self.reset_tracking()
                self._last_effective_classes = current_classes_key

            # 1. Quyết định xem có chạy YOLO hay không (Frame Skipping)
            if self.scheduler.should_detect():
                # Chạy detect thực tế
                detections = self.detector.detect(
                    frame,
                    selected_classes=effective_classes if requested_classes else None,
                )
                self.scheduler.update_detections(detections)
            else:
                # Tái sử dụng bbox cũ
                detections = self.scheduler.get_last_detections()
                self.scheduler.skip_frame()

            # 2. Xử lý nhận diện khuôn mặt nâng cao (Tối ưu hóa hiệu năng bằng Face Tracking)
            face_detections = []
            if self.face_rec_enabled:
                faces = self.face_recognizer.detect_faces(frame)
                current_face_tracks = []
                
                for face in faces:
                    xmin, ymin, w, h = face["bbox"]
                    x2 = xmin + w
                    y2 = ymin + h
                    bbox = (xmin, ymin, x2, y2)
                    
                    # 2.1 So sánh với các khuôn mặt ở frame trước bằng IoU
                    best_match = None
                    best_iou = 0.0
                    for track in self.last_face_tracks:
                        iou = calculate_iou(bbox, track["bbox"])
                        if iou > best_iou:
                            best_iou = iou
                            best_match = track
                            
                    is_matched = False
                    # Nếu tìm thấy vết khuôn mặt cũ trùng khớp cao (IoU > 0.45), tái sử dụng trạng thái
                    if best_match is not None and best_iou > 0.45 and best_match["frames_since_update"] < 15:
                        is_matched = best_match["is_matched"]
                        frames_since_update = best_match["frames_since_update"] + 1
                    else:
                        # Chỉ chạy trích xuất embedding qua ONNX khi khuôn mặt mới xuất hiện hoặc định kỳ
                        face_crop = frame[ymin:y2, xmin:x2]
                        if face_crop.size > 0:
                            embedding = self.face_recognizer.extract_embedding(face_crop)
                            is_matched = False
                            if hasattr(self.face_recognizer, 'registered_embeddings') and self.face_recognizer.registered_embeddings:
                                is_matched, dist = self.face_recognizer.verify_face(embedding)
                        frames_since_update = 0
                        
                    # Lưu thông tin theo dõi cho frame kế tiếp
                    current_face_tracks.append({
                        "bbox": bbox,
                        "is_matched": is_matched,
                        "frames_since_update": frames_since_update
                    })
                    
                    # 2.2 Áp dụng quyết định che phủ (Fail-Closed Privacy)
                    should_mask = False
                    mask_mode = "gaussian_blur"
                    has_registered = (
                        hasattr(self.face_recognizer, 'registered_embeddings')
                        and self.face_recognizer.registered_embeddings
                    )
                    
                    if is_matched:
                        # Xác nhận là chủ sở hữu
                        if self.mask_owner_face:
                            should_mask = True
                            mask_mode = "gaussian_blur"
                    else:
                        # Không khớp: có thể là người lạ HOẶC chủ sở hữu bị nhận sai
                        if self.mask_strangers_face:
                            should_mask = True
                            mask_mode = "mosaic"
                        elif self.mask_owner_face and has_registered:
                            # Fail-closed: nếu đã đăng ký mặt chủ và muốn che chủ,
                            # thì mặt không xác minh được cũng phải che (có thể là chủ bị false negative)
                            should_mask = True
                            mask_mode = "gaussian_blur"
                        
                    if should_mask:
                        face_detections.append({
                            "class_name": "face",
                            "bbox": bbox,
                            "confidence": 1.0,
                            "mask_mode": mask_mode
                        })
                
                self.last_face_tracks = current_face_tracks
            
            # Hợp nhất các hộp phát hiện của YOLOv8 và các hộp che khuôn mặt
            all_detections = detections + face_detections

            # 3. Áp dụng Temporal Smoothing chống nhấp nháy
            smoothed_detections = self.smoothing.update(all_detections)

            # 3. Áp dụng che (Masking) dựa trên mức rủi ro đối tượng
            processed_frame = self.masker.apply_masks(frame, smoothed_detections)

            # 4. Tính toán thông số hiệu năng
            latency = (time.perf_counter() - start_time) * 1000.0
            
            # Tính FPS trung bình trượt (Moving Average FPS)
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
            safe_print(f"PrivacyPipeline error: {e}")
            
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
