"""
face_recognizer.py — Quản lý phát hiện khuôn mặt (OpenCV YuNet) và trích xuất đặc trưng (ONNX MobileFaceNet)
để hỗ trợ nhận diện và so khớp khuôn mặt thời gian thực, tương thích hoàn toàn với Python 3.13.
"""

import hashlib
import json
import os
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from app.utils.console import safe_print


class FaceRecognizer:
    def __init__(
        self,
        threshold=1.1,
        model_dir="models",
        registered_face_path="configs/registered_face.npy",
    ):
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
            safe_print(f"FaceRecognizer: providers={self.ort_session.get_providers()}")
        except Exception as e:
            safe_print(f"FaceRecognizer: preferred providers failed ({e}); retrying CPU")
            self.ort_session = ort.InferenceSession(str(self.model_path), sess_options, providers=['CPUExecutionProvider'])
            
        self.input_name = self.ort_session.get_inputs()[0].name
        output_shape = self.ort_session.get_outputs()[0].shape
        self.embedding_dimension = (
            int(output_shape[-1]) if isinstance(output_shape[-1], int) else 512
        )
        
        # 4. Tải khuôn mặt đã đăng ký nếu có
        self.registered_embeddings = self.load_registered_face()

    # SHA256 checksums đã xác minh cho các phiên bản ONNX model cụ thể
    _MODEL_CHECKSUMS = {
        "face_detection_yunet.onnx": None,  # None = skip check (first download), sẽ cập nhật sau khi verify thủ công
        "mobilefacenet.onnx": None,
    }

    def _ensure_models_exist(self):
        """Tải mô hình YuNet và MobileFaceNet từ nguồn uy tín nếu chưa tồn tại cục bộ."""
        downloads = [
            (self.detector_path, "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"),
            (self.model_path, "https://huggingface.co/WePrompt/buffalo_sc/resolve/main/w600k_mbf.onnx")
        ]
        
        for path, url in downloads:
            # File hợp lệ khi tồn tại và có dung lượng lớn hơn 50KB
            if path.exists() and path.stat().st_size > 50 * 1024:
                continue
                
            safe_print(f"FaceRecognizer: downloading missing asset {path.name} from {url}")
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
                    safe_print(f"FaceRecognizer: SHA256 verified {path.name}")

                safe_print(f"FaceRecognizer: downloaded {path.name}")
            except Exception as e:
                safe_print(f"FaceRecognizer: download failed for {url}: {e}")
                if path.exists():
                    path.unlink()
                raise RuntimeError(
                    f"❌ Không thể tự động tải {path.name}. "
                    f"Vui lòng tải thủ công và đặt vào thư mục models/."
                ) from e

    def extract_embedding(self, face_img):
        """Trích xuất vector nhúng 512 chiều từ ảnh khuôn mặt (cắt ra)."""
        # Tiền xử lý theo chuẩn đầu vào MobileFaceNet: size 112x112, BGR sang RGB, chuẩn hóa [-1, 1]
        face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        face_resized = cv2.resize(face_rgb, (112, 112))
        
        # Chuẩn hóa về khoảng [-1, 1]
        face_normalized = (face_resized.astype(np.float32) - 127.5) / 128.0
        
        # Chuyển đổi định dạng từ HWC sang CHW
        face_input = np.transpose(face_normalized, (2, 0, 1))
        # Thêm chiều batch (1, 3, 112, 112)
        face_input = np.expand_dims(face_input, axis=0)
        
        # Thực thi ONNX inference
        embeddings = self.ort_session.run(None, {self.input_name: face_input})[0]
        embedding = embeddings[0]
        
        # L2 Normalize vector nhúng để so khớp khoảng cách Euclidean chính xác
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
            
        return embedding

    def detect_faces(self, frame):
        """Phát hiện tất cả khuôn mặt trong frame bằng YuNet.
        Trả về danh sách dict chứa coordinates: [xmin, ymin, w, h] (dạng pixel tuyệt đối).
        """
        h, w, _ = frame.shape
        # Chỉ set input size khi kích thước frame thay đổi
        if not hasattr(self, '_last_input_size') or self._last_input_size != (w, h):
            self.detector.setInputSize((w, h))
            self._last_input_size = (w, h)
        _, faces = self.detector.detect(frame)
        
        results = []
        if faces is not None:
            for face in faces:
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
                        "bbox": [xmin, ymin, width, height],
                        "face_object": face
                    })
        return results

    def estimate_head_pose(self, face_object):
        """Ước lượng hướng quay đầu ngang (Left/Right/Frontal) và dọc (Pitch) dựa trên tỉ lệ khoảng cách mắt-mũi-miệng.
        Hệ thống webcam đã lật gương (mirrored frame) nên tỉ lệ đảo ngược:
          - -2: Cúi/Ngửa đầu (Pitch lỗi)
          - 0: Nhìn thẳng
          - 1: Nghiêng trái
          - 2: Nghiêng phải
        """
        # Tọa độ X của mắt và mũi để ước lượng Yaw (trái/phải)
        x_eye1 = face_object[4]
        x_eye2 = face_object[6]
        x_nose = face_object[8]
        
        x_min = min(x_eye1, x_eye2)
        x_max = max(x_eye1, x_eye2)
        
        # Tọa độ Y của mắt, mũi, miệng để ước lượng Pitch (cúi/ngửa)
        y_eye1 = face_object[5]
        y_eye2 = face_object[7]
        y_nose = face_object[9]
        y_mouth1 = face_object[11]
        y_mouth2 = face_object[13]
        
        y_eyes = (y_eye1 + y_eye2) / 2.0
        y_mouth = (y_mouth1 + y_mouth2) / 2.0
        
        d_eyes_nose = y_nose - y_eyes
        d_nose_mouth = y_mouth - y_nose
        v_ratio = d_eyes_nose / (d_nose_mouth + 1e-5)
        
        # 1. Kiểm tra Pitch (Cúi/Ngửa đầu) trước
        # Giá trị v_ratio chuẩn cho tư thế nhìn thẳng thông thường nằm trong khoảng [0.55, 1.65]
        if v_ratio < 0.55 or v_ratio > 1.65:
            pose = -2  # Cúi hoặc ngửa đầu quá nhiều
            ratio = v_ratio
        # 2. Nếu Pitch hợp lệ, tiếp tục kiểm tra Yaw (Nghiêng trái/phải)
        elif x_nose < x_min:
            pose = 1  # Nghiêng trái cực hạn (mũi vượt quá mắt trái trên màn hình)
            ratio = -1.0
        elif x_nose > x_max:
            pose = 2  # Nghiêng phải cực hạn (mũi vượt quá mắt phải trên màn hình)
            ratio = 999.0
        else:
            d_left = x_nose - x_min
            d_right = x_max - x_nose
            ratio = d_left / (d_right + 1e-5)
            
            # Ngưỡng tỷ lệ Yaw được hiệu chuẩn qua thực nghiệm:
            if ratio < 0.6:
                pose = 1  # Nghiêng trái
            elif ratio > 1.6:
                pose = 2  # Nghiêng phải
            else:
                pose = 0  # Nhìn thẳng
            
        return pose

    def register_face(self, frame, face_bbox):
        """Chụp khuôn mặt và lưu làm mẫu mặt thẳng duy nhất (tương thích ngược)."""
        xmin, ymin, w, h = face_bbox
        face_crop = frame[ymin:ymin+h, xmin:xmin+w]
        
        if face_crop.size == 0:
            return False
            
        embedding = self.extract_embedding(face_crop)
        self.registered_embeddings = [embedding]
        return self.save_registered_faces()

    def register_face_pose(self, frame, face_bbox, pose_index):
        """Chụp khuôn mặt từ frame, trích xuất và lưu vector nhúng cho góc mặt cụ thể (pose_index)."""
        xmin, ymin, w, h = face_bbox
        face_crop = frame[ymin:ymin+h, xmin:xmin+w]
        
        if face_crop.size == 0:
            return False
            
        embedding = self.extract_embedding(face_crop)
        
        # Đảm bảo self.registered_embeddings là một danh sách hợp lệ
        if not hasattr(self, 'registered_embeddings') or not isinstance(self.registered_embeddings, list):
            self.registered_embeddings = []
            
        # Đảm bảo danh sách đủ phần tử chứa pose_index
        while len(self.registered_embeddings) <= pose_index:
            self.registered_embeddings.append(None)
            
        self.registered_embeddings[pose_index] = embedding
        safe_print(f"FaceRecognizer: captured enrollment pose {pose_index}")
        return True

    def save_registered_faces(self):
        """Atomically persist validated embeddings and non-identifying metadata."""
        if not hasattr(self, 'registered_embeddings') or not self.registered_embeddings:
            return False
            
        # Loại bỏ các góc bị quét lỗi (None)
        valid_embeddings = [emb for emb in self.registered_embeddings if emb is not None]
        if not valid_embeddings:
            return False
            
        payload = np.asarray(valid_embeddings, dtype=np.float32)
        if payload.ndim != 2 or payload.shape[1] != self.embedding_dimension:
            return False
        if not np.isfinite(payload).all():
            return False

        self.registered_face_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.registered_face_path.with_name(
            f".{self.registered_face_path.name}.tmp"
        )
        with temp_path.open("wb") as handle:
            np.save(handle, payload, allow_pickle=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, self.registered_face_path)

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
        safe_print(f"FaceRecognizer: saved {len(valid_embeddings)} enrollment embeddings")
        return True

    def load_registered_face(self):
        """Tải danh sách vector nhúng các mẫu mặt của chủ sở hữu."""
        if self.registered_face_path.exists():
            try:
                embeddings = np.load(str(self.registered_face_path), allow_pickle=False)
                if embeddings.ndim == 1:
                    embeddings = embeddings.reshape(1, -1)
                if (
                    embeddings.ndim != 2
                    or embeddings.shape[1] != self.embedding_dimension
                    or not np.isfinite(embeddings).all()
                ):
                    raise ValueError("invalid embedding shape or values")
                if embeddings.shape[0] == 1:
                    safe_print("FaceRecognizer: loaded 1 enrollment embedding")
                else:
                    safe_print(
                        f"FaceRecognizer: loaded {embeddings.shape[0]} enrollment embeddings"
                    )
                return [row.astype(np.float32, copy=True) for row in embeddings]
            except Exception as e:
                safe_print(f"FaceRecognizer: enrollment template load failed: {e}")
        return []

    def delete_registered_faces(self):
        """Delete the local biometric template and clear it from memory."""
        self.registered_embeddings = []
        removed = False
        for path in (self.registered_face_path, self._metadata_path()):
            try:
                path.unlink()
                removed = True
            except FileNotFoundError:
                pass
        return removed

    def _metadata_path(self):
        return self.registered_face_path.with_suffix(
            self.registered_face_path.suffix + ".json"
        )

    @staticmethod
    def _sha256(path):
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def verify_face(self, face_embedding):
        """So khớp vector nhúng hiện tại với danh sách mẫu chủ sở hữu bằng khoảng cách Euclidean.
        Trả về True nếu khoảng cách nhỏ nhất nhỏ hơn ngưỡng threshold.
        """
        if not hasattr(self, 'registered_embeddings') or not self.registered_embeddings:
            return False, 999.0
            
        distances = []
        for reg_emb in self.registered_embeddings:
            if reg_emb is not None:
                dist = np.linalg.norm(face_embedding - reg_emb)
                distances.append(dist)
                
        if not distances:
            return False, 999.0
            
        min_dist = min(distances)
        is_matched = bool(min_dist < self.threshold)
        return is_matched, float(min_dist)
