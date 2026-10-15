"""
face_recognizer.py — Quản lý phát hiện khuôn mặt (OpenCV YuNet) và trích xuất đặc trưng (ONNX MobileFaceNet)
để hỗ trợ nhận diện và so khớp khuôn mặt thời gian thực, tương thích hoàn toàn với Python 3.13.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import urllib.request
from collections.abc import Sequence
from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import onnxruntime as ort

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class FaceRecognizer:
    _lock: threading.RLock
    threshold: float
    model_dir: Path
    detector_path: Path
    model_path: Path
    registered_face_path: Path
    detector: Any
    ort_session: ort.InferenceSession
    input_name: str
    embedding_dimension: int
    registered_embeddings: list[np.ndarray | None]

    def __init__(
        self,
        threshold: float = 1.1,
        model_dir: str | Path = "models",
        registered_face_path: str | Path = "configs/registered_face.npy",
    ) -> None:
        self._lock = threading.RLock()
        self.threshold = threshold
        self.model_dir = Path(model_dir)
        self.detector_path = self.model_dir / "face_detection_yunet.onnx"
        self.model_path = self.model_dir / "mobilefacenet.onnx"
        self.registered_face_path = Path(registered_face_path)
        
        # Tạo thư mục chứa mô hình nếu chưa có
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Đảm bảo các mô hình YuNet và MobileFaceNet ONNX tồn tại
        self._ensure_models_exist()
        
        # 2. Khởi tạo OpenCV YuNet Face Detector
        # YuNet hoạt động siêu tốc trên CPU/GPU và tương thích 100% với Python 3.13
        self.detector = cv2.FaceDetectorYN.create(
            model=str(self.detector_path),
            config="",
            input_size=(320, 320),
            score_threshold=0.6,
            nms_threshold=0.3,
            top_k=50
        )
        
        # 3. Khởi tạo ONNX Runtime Session cho MobileFaceNet với cấu hình tối ưu
        available_providers = set(ort.get_available_providers())
        providers = [
            provider
            for provider in ('CUDAExecutionProvider', 'CPUExecutionProvider')
            if provider in available_providers
        ]
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.intra_op_num_threads = 2  # Tránh hao phí chuyển ngữ cảnh thread của CPU
        
        try:
            self.ort_session = ort.InferenceSession(str(self.model_path), sess_options, providers=providers)
            logger.info("FaceRecognizer: providers=%s", self.ort_session.get_providers())
        except Exception as e:
            logger.warning("FaceRecognizer: preferred providers failed (%s); retrying CPU", e)
            self.ort_session = ort.InferenceSession(str(self.model_path), sess_options, providers=['CPUExecutionProvider'])
            
        self.input_name = self.ort_session.get_inputs()[0].name
        output_shape = self.ort_session.get_outputs()[0].shape
        self.embedding_dimension = (
            int(output_shape[-1]) if isinstance(output_shape[-1], int) else 512
        )
        
        # 4. Tải khuôn mặt đã đăng ký nếu có
        self.registered_embeddings = self.load_registered_face()

    def _get_lock(self) -> threading.RLock:
        """Lazy lock accessor so instances created via __new__ in tests still have a lock."""
        lock = getattr(self, "_lock", None)
        if lock is None:
            lock = threading.RLock()
            self._lock = lock
        return lock

    # SHA256 checksums đã xác minh cho các phiên bản ONNX model cụ thể
    _MODEL_CHECKSUMS: dict[str, str] = {
        "face_detection_yunet.onnx": "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
        "mobilefacenet.onnx": "9cc6e4a75f0e2bf0b1aed94578f144d15175f357bdc05e815e5c4a02b319eb4f",
    }

    def _ensure_models_exist(self) -> None:
        """Tải mô hình YuNet và MobileFaceNet từ nguồn uy tín nếu chưa tồn tại cục bộ."""
        downloads = [
            (self.detector_path, "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"),
            (self.model_path, "https://huggingface.co/WePrompt/buffalo_sc/resolve/main/w600k_mbf.onnx")
        ]
        
        for path, url in downloads:
            # File hợp lệ khi tồn tại và có dung lượng lớn hơn 50KB
            if path.exists() and path.stat().st_size > 50 * 1024:
                continue
                
            logger.info("FaceRecognizer: downloading missing asset %s from %s", path.name, url)
            try:
                # Thiết lập User-Agent và timeout để tránh bị chặn/hang
                req = urllib.request.Request(
                    url, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                with urllib.request.urlopen(req, timeout=60) as response, open(path, 'wb') as out_file:
                    out_file.write(response.read())
                
                if not path.exists() or path.stat().st_size <= 50 * 1024:
                    raise ValueError("Dung lượng file tải về quá nhỏ.")

                # Xác minh SHA256 nếu có checksum đã biết
                expected_hash = self._MODEL_CHECKSUMS.get(path.name)
                if expected_hash is not None:
                    actual_hash = self._sha256(path)
                    if actual_hash != expected_hash:
                        path.unlink(missing_ok=True)
                        raise ValueError(
                            f"SHA256 mismatch cho {path.name}: "
                            f"expected {expected_hash[:16]}..., got {actual_hash[:16]}..."
                        )
                    logger.info("FaceRecognizer: SHA256 verified %s", path.name)

                logger.info("FaceRecognizer: downloaded %s", path.name)
            except Exception as e:
                logger.error("FaceRecognizer: download failed for %s: %s", url, e)
                if path.exists():
                    path.unlink()
                raise RuntimeError(
                    f"❌ Không thể tự động tải {path.name}. "
                    f"Vui lòng tải thủ công và đặt vào thư mục models/."
                ) from e

    # Tọa độ chuẩn 5 điểm landmark ArcFace / InsightFace (112x112)
    _ARCFACE_DST: np.ndarray = np.array(
        [
            [38.2946, 51.6963],
            [73.5318, 51.5014],
            [56.0252, 71.7366],
            [41.5493, 92.3655],
            [70.7299, 92.2041],
        ],
        dtype=np.float32,
    )

    @classmethod
    def align_face(
        cls, frame: np.ndarray, face_object: Sequence[float] | np.ndarray | None
    ) -> np.ndarray | None:
        """Căn chỉnh khuôn mặt về chuẩn 112x112 bằng phép biến đổi đồng dạng 5 điểm landmark (ArcFace norm_crop)."""
        if frame is None or face_object is None or len(face_object) < 14:
            return None
        try:
            kps = np.asarray(face_object[4:14], dtype=np.float32).reshape(5, 2)
            if not np.isfinite(kps).all():
                return None
            matrix, _ = cv2.estimateAffinePartial2D(kps, cls._ARCFACE_DST, method=cv2.LMEDS)
            if matrix is None:
                return None
            aligned = cv2.warpAffine(
                frame,
                matrix,
                (112, 112),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REPLICATE,
            )
            return aligned if aligned is not None and aligned.size > 0 else None
        except Exception:
            return None

    def extract_embedding(self, face_img: np.ndarray) -> np.ndarray:
        """Trích xuất vector nhúng 512 chiều từ ảnh khuôn mặt (cắt ra hoặc đã align 112x112)."""
        # Tiền xử lý theo chuẩn đầu vào MobileFaceNet: size 112x112, BGR sang RGB, chuẩn hóa [-1, 1]
        face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        if face_rgb.shape[:2] != (112, 112):
            face_resized = cv2.resize(face_rgb, (112, 112), interpolation=cv2.INTER_LINEAR)
        else:
            face_resized = face_rgb

        # Chuẩn hóa về khoảng [-1, 1]
        face_normalized = (face_resized.astype(np.float32) - 127.5) / 128.0

        # Chuyển đổi định dạng từ HWC sang CHW
        face_input = np.transpose(face_normalized, (2, 0, 1))
        # Thêm chiều batch (1, 3, 112, 112)
        face_input = np.expand_dims(face_input, axis=0)

        # Thực thi ONNX inference
        embeddings = self.ort_session.run(None, {self.input_name: face_input})[0]
        embedding: np.ndarray = embeddings[0]

        # L2 Normalize vector nhúng để so khớp khoảng cách Euclidean chính xác
        norm = float(np.linalg.norm(embedding))
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def detect_faces(self, frame: np.ndarray) -> list[dict[str, Any]]:
        """Phát hiện tất cả khuôn mặt trong frame bằng YuNet.
        Tối ưu hiệu năng: thu nhỏ ảnh lớn (ví dụ 640x480 -> 320x240) khi chạy YuNet,
        sau đó quy đổi tọa độ bbox và 5 điểm landmark về kích thước gốc (nhanh hơn ~5 lần).
        Trả về danh sách dict chứa coordinates: [xmin, ymin, w, h] (dạng pixel tuyệt đối).
        """
        if frame is None or getattr(frame, "size", 0) == 0 or not np.any(frame):
            return []

        h, w = frame.shape[:2]
        max_dim = max(w, h)
        if max_dim > 320:
            scale = 320.0 / float(max_dim)
            det_w = max(16, int(round(w * scale)))
            det_h = max(16, int(round(h * scale)))
            det_frame = cv2.resize(frame, (det_w, det_h), interpolation=cv2.INTER_LINEAR)
            inv_scale_x = float(w) / float(det_w)
            inv_scale_y = float(h) / float(det_h)
        else:
            det_w, det_h = w, h
            det_frame = frame
            inv_scale_x = 1.0
            inv_scale_y = 1.0

        # Chỉ set input size khi kích thước đưa vào YuNet thay đổi
        if not hasattr(self, "_last_input_size") or self._last_input_size != (det_w, det_h):
            self.detector.setInputSize((det_w, det_h))
            self._last_input_size = (det_w, det_h)
        _, faces = self.detector.detect(det_frame)

        results: list[dict[str, Any]] = []
        if faces is not None:
            for raw_face in faces:
                face = raw_face.copy()
                if inv_scale_x != 1.0 or inv_scale_y != 1.0:
                    face[0:14:2] *= inv_scale_x
                    face[1:14:2] *= inv_scale_y
                bbox = face[0:4].astype(int)
                xmin, ymin, width, height = bbox

                # Giới hạn tọa độ trong biên ảnh (fix: trừ offset khi clip)
                if xmin < 0:
                    width += xmin  # giảm width theo phần bị clip
                    xmin = 0
                if ymin < 0:
                    height += ymin
                    ymin = 0
                width = min(width, w - xmin)
                height = min(height, h - ymin)

                if width > 10 and height > 10:
                    results.append({
                        "bbox": [int(xmin), int(ymin), int(width), int(height)],
                        "face_object": face,
                    })
        return results

    def estimate_head_pose(self, face_object: Sequence[float] | np.ndarray) -> int:
        """Ước lượng hướng quay đầu ngang (Left/Right/Frontal) và dọc (Pitch) dựa trên tỉ lệ khoảng cách mắt-mũi-miệng.
        Hệ thống webcam đã lật gương (mirrored frame) nên tỉ lệ đảo ngược:
          - -2: Cúi/Ngửa đầu (Pitch lỗi)
          - 0: Nhìn thẳng
          - 1: Nghiêng trái
          - 2: Nghiêng phải
        """
        # Tọa độ X của mắt và mũi để ước lượng Yaw (trái/phải)
        x_eye1 = float(face_object[4])
        x_eye2 = float(face_object[6])
        x_nose = float(face_object[8])

        x_min = min(x_eye1, x_eye2)
        x_max = max(x_eye1, x_eye2)

        # Tọa độ Y của mắt, mũi, miệng để ước lượng Pitch (cúi/ngửa)
        y_eye1 = float(face_object[5])
        y_eye2 = float(face_object[7])
        y_nose = float(face_object[9])
        y_mouth1 = float(face_object[11])
        y_mouth2 = float(face_object[13])

        y_eyes = (y_eye1 + y_eye2) / 2.0
        y_mouth = (y_mouth1 + y_mouth2) / 2.0

        d_eyes_nose = y_nose - y_eyes
        d_nose_mouth = y_mouth - y_nose
        v_ratio = d_eyes_nose / (d_nose_mouth + 1e-5)

        # 1. Kiểm tra Pitch (Cúi/Ngửa đầu) trước
        if v_ratio < 0.45 or v_ratio > 1.80:
            pose = -2  # Cúi hoặc ngửa đầu quá nhiều
        # 2. Nếu Pitch hợp lệ, tiếp tục kiểm tra Yaw (Nghiêng trái/phải ~15°-30° tự nhiên)
        elif x_nose < x_min:
            pose = 1  # Nghiêng trái
        elif x_nose > x_max:
            pose = 2  # Nghiêng phải
        else:
            d_left = x_nose - x_min
            d_right = x_max - x_nose
            ratio = d_left / (d_right + 1e-5)

            if ratio < 0.76:
                pose = 1  # Nghiêng trái nhẹ (15°-25°)
            elif ratio > 1.32:
                pose = 2  # Nghiêng phải nhẹ (15°-25°)
            else:
                pose = 0  # Nhìn thẳng

        return pose

    def register_face(self, frame: np.ndarray, face_bbox: Sequence[int]) -> bool:
        """Chụp khuôn mặt và lưu làm mẫu mặt thẳng duy nhất (tương thích ngược)."""
        xmin, ymin, w, h = face_bbox
        face_crop = frame[ymin : ymin + h, xmin : xmin + w]

        if face_crop.size == 0:
            return False

        embedding = self.extract_embedding(face_crop)
        with self._get_lock():
            self.registered_embeddings = [embedding]
            self._aligned_pose_embeddings = {}
            self._gallery_cache_key = None
            return self.save_registered_faces()

    def register_face_pose(
        self,
        frame: np.ndarray,
        face_bbox: Sequence[int],
        pose_index: int,
        face_object: Sequence[float] | np.ndarray | None = None,
    ) -> bool:
        """Chụp khuôn mặt từ frame, trích xuất cả vector chuẩn hóa 5-point landmark (ArcFace)
        và vector vùng mặt (crop) cho góc mặt cụ thể (pose_index).
        """
        xmin, ymin, w, h = face_bbox
        face_crop = frame[ymin : ymin + h, xmin : xmin + w]

        if face_crop.size == 0:
            return False

        embedding_crop = self.extract_embedding(face_crop)
        embedding_aligned: np.ndarray | None = None
        if face_object is not None:
            aligned_img = self.align_face(frame, face_object)
            if aligned_img is not None:
                embedding_aligned = self.extract_embedding(aligned_img)

        with self._get_lock():
            if not hasattr(self, "registered_embeddings") or not isinstance(
                self.registered_embeddings, list
            ):
                self.registered_embeddings = []
            if not hasattr(self, "_aligned_pose_embeddings") or not isinstance(
                self._aligned_pose_embeddings, dict
            ):
                self._aligned_pose_embeddings = {}

            while len(self.registered_embeddings) <= pose_index:
                self.registered_embeddings.append(None)

            # Lưu vector chính (nếu có aligned thì lưu cả hai khi persist để tương thích cả 2 chế độ)
            self.registered_embeddings[pose_index] = (
                embedding_aligned if embedding_aligned is not None else embedding_crop
            )
            if embedding_aligned is not None:
                self._aligned_pose_embeddings[pose_index] = embedding_crop
            self._gallery_cache_key = None
        logger.info("FaceRecognizer: captured enrollment pose %d", pose_index)
        return True

    def save_registered_faces(self) -> bool:
        """Atomically persist validated embeddings and non-identifying metadata."""
        with self._get_lock():
            if not hasattr(self, "registered_embeddings") or not self.registered_embeddings:
                return False

            # Loại bỏ các góc bị quét lỗi (None)
            valid_embeddings = [emb for emb in self.registered_embeddings if emb is not None]
            if not valid_embeddings:
                return False

            # Bổ sung các vector bổ trợ (crop + aligned) nếu được thu thập trong quá trình đăng ký
            extra_crops = list(getattr(self, "_aligned_pose_embeddings", {}).values())
            all_to_save = list(valid_embeddings) + [e for e in extra_crops if e is not None]

            payload = np.asarray(all_to_save, dtype=np.float32)
            if payload.ndim != 2 or payload.shape[1] != self.embedding_dimension:
                return False
            if not np.isfinite(payload).all():
                return False

            self.registered_face_path.parent.mkdir(parents=True, exist_ok=True)
            from app.utils.crypto import save_encrypted_array

            if not save_encrypted_array(payload, self.registered_face_path):
                return False

            metadata = {
                "schema_version": 1,
                "embedding_dimension": self.embedding_dimension,
                "embedding_count": int(payload.shape[0]),
                "model_sha256": self._sha256(self.model_path),
                "created_at": datetime.now(UTC).isoformat(),
            }
            metadata_path = self._metadata_path()
            metadata_temp = metadata_path.with_name(f".{metadata_path.name}.tmp")
            metadata_temp.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            os.replace(metadata_temp, metadata_path)
            self.registered_embeddings = [row.astype(np.float32, copy=True) for row in payload]
            self._aligned_pose_embeddings = {}
            self._gallery_cache_key = None
            logger.info("FaceRecognizer: saved %d enrollment embeddings", len(all_to_save))
            return True

    def load_registered_face(self) -> list[np.ndarray | None]:
        """Tải danh sách vector nhúng các mẫu mặt của chủ sở hữu (có xác minh metadata)."""
        with self._get_lock():
            self._gallery_cache_key = None
            if self.registered_face_path.exists():
                try:
                    # Xác minh metadata JSON nếu tồn tại (backward compatible với legacy file không có .json)
                    metadata_path = self._metadata_path()
                    if metadata_path.exists():
                        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                        expected_sha = metadata.get("model_sha256")
                        if (
                            expected_sha
                            and hasattr(self, "model_path")
                            and Path(self.model_path).exists()
                        ):
                            actual_sha = self._sha256(self.model_path)
                            if actual_sha != expected_sha:
                                raise ValueError(
                                    f"embedding model_sha256 mismatch (expected {expected_sha[:12]}..., got {actual_sha[:12]}...)"
                                )
                        meta_dim = metadata.get("embedding_dimension")
                        if meta_dim is not None and int(meta_dim) != self.embedding_dimension:
                            raise ValueError(
                                f"metadata embedding_dimension mismatch ({meta_dim} != {self.embedding_dimension})"
                            )

                    from app.utils.crypto import load_encrypted_array

                    embeddings = load_encrypted_array(self.registered_face_path)
                    if embeddings is None:
                        return []
                    if embeddings.ndim == 1:
                        embeddings = embeddings.reshape(1, -1)
                    if (
                        embeddings.ndim != 2
                        or embeddings.shape[1] != self.embedding_dimension
                        or not np.isfinite(embeddings).all()
                    ):
                        raise ValueError("invalid embedding shape or values")
                    if embeddings.shape[0] == 1:
                        logger.info("FaceRecognizer: loaded 1 enrollment embedding")
                    else:
                        logger.info(
                            "FaceRecognizer: loaded %d enrollment embeddings",
                            embeddings.shape[0],
                        )
                    return [row.astype(np.float32, copy=True) for row in embeddings]
                except Exception as e:
                    logger.warning("FaceRecognizer: enrollment template load failed: %s", e)
            return []

    def delete_registered_faces(self) -> bool:
        """Delete the local biometric template and clear it from memory."""
        with self._get_lock():
            self.registered_embeddings = []
            self._aligned_pose_embeddings = {}
            self._gallery_cache_key = None
            removed = False
            for path in (self.registered_face_path, self._metadata_path()):
                try:
                    path.unlink()
                    removed = True
                except FileNotFoundError:
                    pass
            return removed

    def _metadata_path(self) -> Path:
        return self.registered_face_path.with_suffix(
            self.registered_face_path.suffix + ".json"
        )

    @staticmethod
    def _sha256(path: str | Path) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _get_gallery_embeddings(self) -> list[np.ndarray]:
        """Tổng hợp bộ mẫu đối sánh gồm các vector gốc + Centroid Prototype + Geodesic Midpoints."""
        lock_fn = getattr(self, "_get_lock", None)
        lock = lock_fn() if callable(lock_fn) else nullcontext()
        with lock:
            if not hasattr(self, "registered_embeddings") or not self.registered_embeddings:
                return []
            valid = [emb for emb in self.registered_embeddings if emb is not None]
            if not valid:
                return []
            extra = [
                emb
                for emb in getattr(self, "_aligned_pose_embeddings", {}).values()
                if emb is not None
            ]
            all_valid = valid + extra
            cache_key = tuple(id(e) for e in all_valid)
            if (
                getattr(self, "_gallery_cache_key", None) == cache_key
                and hasattr(self, "_gallery_cache")
            ):
                return self._gallery_cache

            gallery: list[np.ndarray] = list(all_valid)
            n = len(all_valid)
            if n >= 2:
                # 1. Global Centroid Prototype (khử nhiễu góc nghiêng trái/phải)
                mean_vec = np.mean(all_valid, axis=0)
                norm = float(np.linalg.norm(mean_vec))
                if norm > 1e-6:
                    gallery.append((mean_vec / norm).astype(np.float32))

                # 2. Pairwise Geodesic Midpoints (nội suy mặt cầu đơn vị giữa các góc mặt)
                for i in range(n):
                    for j in range(i + 1, n):
                        mid = all_valid[i] + all_valid[j]
                        mid_norm = float(np.linalg.norm(mid))
                        if mid_norm > 1e-6:
                            gallery.append((mid / mid_norm).astype(np.float32))

            self._gallery_cache_key = cache_key
            self._gallery_cache = gallery
            return gallery

    def verify_face(self, face_embedding: np.ndarray) -> tuple[bool, float]:
        """So khớp vector nhúng hiện tại với bộ mẫu chủ sở hữu (bao gồm Centroid & Geodesic Prototypes).
        Trả về True nếu khoảng cách nhỏ nhất nhỏ hơn ngưỡng threshold.
        """
        gallery = FaceRecognizer._get_gallery_embeddings(self)
        if not gallery:
            return False, 999.0

        distances = [float(np.linalg.norm(face_embedding - reg_emb)) for reg_emb in gallery]
        if not distances:
            return False, 999.0

        min_dist = min(distances)
        is_matched = bool(min_dist < self.threshold)
        return is_matched, float(min_dist)

    def verify_face_region(
        self, frame: np.ndarray, face: dict[str, Any]
    ) -> tuple[bool, float, bool]:
        """Xác thực khuôn mặt đa biểu diễn (Dual-Probe: 5-Point ArcFace Aligned + Bounding-Box Crop).
        Trả về: (is_matched, best_distance, verify_failed)
        """
        xmin, ymin, w, h = face["bbox"]
        fh, fw = frame.shape[:2]
        x1 = max(0, int(xmin))
        y1 = max(0, int(ymin))
        x2 = min(fw, int(xmin + w))
        y2 = min(fh, int(ymin + h))
        face_crop = frame[y1:y2, x1:x2]
        if face_crop.size == 0:
            return False, 999.0, True

        try:
            candidates: list[np.ndarray] = []
            emb_crop = self.extract_embedding(face_crop)
            if emb_crop is not None:
                candidates.append(emb_crop)
                is_matched_crop, dist_crop = self.verify_face(emb_crop)
                # Nếu khớp rõ ràng ngay từ probe đầu tiên thì trả về tức thì (1 ONNX pass)
                if is_matched_crop and dist_crop < self.threshold * 0.88:
                    return True, dist_crop, False

            face_obj = face.get("face_object")
            if face_obj is not None:
                aligned_img = self.align_face(frame, face_obj)
                if aligned_img is not None:
                    emb_aligned = self.extract_embedding(aligned_img)
                    if emb_aligned is not None:
                        candidates.append(emb_aligned)

            if not candidates:
                return False, 999.0, True

            best_dist = 999.0
            best_matched = False
            for emb in candidates:
                matched, dist = self.verify_face(emb)
                if dist < best_dist:
                    best_dist = dist
                    best_matched = matched

            return best_matched, best_dist, False
        except Exception as exc:
            logger.warning("verify_face_region error: %s", exc)
            return False, 999.0, True



