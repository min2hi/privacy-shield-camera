import os

import cv2
import numpy as np
from ultralytics import YOLO

from app.core.model_bundle import ModelManifest
from app.utils.console import safe_print

HYBRID_PRIVACY_CLASSES = frozenset({
    "cell phone",
    "id_card",
    "credit_card",
    "qr_code",
    "receipt",
    "smartphone_screen",
    "document",
})


class Detector:
    def __init__(
        self,
        model_path="models/yolov8n.pt",
        confidence=0.25,
        iou=0.45,
        device="cpu",
        image_size=640,
        manifest_path=None,
    ):
        self.model_path = model_path
        self.confidence = confidence
        self.iou = iou
        self.device = device
        self.image_size = image_size
        self.manifest = ModelManifest.load(manifest_path) if manifest_path else None
        self.model = None
        self._qr_detector = cv2.QRCodeDetector()
        self.load_model()

    @property
    def supported_class_names(self):
        """Return the exact class names exposed by the loaded model + hybrid CV pipeline."""
        if self.model is None:
            return set()
        if self.manifest is not None:
            return set(self.manifest.supported_privacy_classes)
        names = self.model.names
        values = names.values() if isinstance(names, dict) else names
        return {str(name) for name in values} | set(HYBRID_PRIVACY_CLASSES)

    def load_model(self):
        """
        Tải mô hình YOLOv8 từ đường dẫn cấu hình.
        Nếu không có sẵn tại đường dẫn, Ultralytics sẽ tự tải bản pretrained chính thức từ repo của họ.
        """
        model_dir = os.path.dirname(self.model_path)
        if model_dir and not os.path.exists(model_dir):
            os.makedirs(model_dir, exist_ok=True)

        safe_print(f"Detector: loading YOLO model from {self.model_path}")
        if self.manifest is not None:
            self.manifest.validate_asset(self.model_path)
        self.model = YOLO(self.model_path)
        if self.manifest is not None:
            names = self.model.names
            runtime_names = set(names.values() if isinstance(names, dict) else names)
            runtime_names |= set(HYBRID_PRIVACY_CLASSES)
            self.manifest.validate_runtime_classes(runtime_names)
        safe_print("Detector: model loaded")

    def detect(self, frame, selected_classes=None):
        """
        Chạy phát hiện đối tượng trên một frame ảnh (kết hợp YOLOv8 + OpenCV QR/Card/Document).
        selected_classes: Danh sách tên các class cần lọc. Nếu None, nhận diện tất cả các class.
        Trả về: Danh sách các dict [{ 'class_name': ..., 'confidence': ..., 'bbox': (x1, y1, x2, y2) }]
        """
        if self.model is None or frame is None or getattr(frame, "size", 0) == 0:
            return []

        results = self.model.predict(
            source=frame,
            conf=self.confidence,
            iou=self.iou,
            device=self.device,
            verbose=False,
            imgsz=self.image_size,
        )

        detections = []
        if len(results) > 0:
            result = results[0]
            boxes = result.boxes

            for box in boxes:
                cls_id = int(box.cls[0].item())
                class_name = str(self.model.names[cls_id])
                if selected_classes is not None and class_name not in selected_classes:
                    continue

                confidence = float(box.conf[0].item())
                xyxy = box.xyxy[0].cpu().numpy().reshape(-1)
                x1, y1, x2, y2 = map(int, xyxy[:4])

                detections.append({
                    "class_name": class_name,
                    "confidence": confidence,
                    "bbox": (x1, y1, x2, y2),
                })

        # Phát hiện bổ sung QR Code, Thẻ CCCD/Ngân hàng, Hóa đơn, Tài liệu qua OpenCV
        detections.extend(self._detect_qr_and_cards(frame, selected_classes))
        return detections

    def _detect_qr_and_cards(self, frame, selected_classes=None):
        """Phát hiện thời gian thực mã QR và các vật thể dạng thẻ/hóa đơn/tài liệu."""
        extra = []
        if not isinstance(frame, np.ndarray) or frame.ndim != 3:
            return extra
        h, w = frame.shape[:2]
        if h < 40 or w < 40:
            return extra
        # Bỏ qua frame đen hoàn toàn (như trong unit test np.zeros) để tránh tốn CPU
        if not np.any(frame):
            return extra

        def want(cls_name):
            return selected_classes is None or cls_name in selected_classes

        # 1. Phát hiện mã QR bằng OpenCV QRCodeDetector
        if want("qr_code"):
            try:
                qr_det = getattr(self, "_qr_detector", None)
                if qr_det is None:
                    qr_det = cv2.QRCodeDetector()
                    self._qr_detector = qr_det
                ok, points = qr_det.detectMulti(frame)
                if ok and points is not None:
                    for pts in points:
                        pts_arr = np.array(pts, dtype=np.int32).reshape(-1, 2)
                        x1 = int(np.clip(np.min(pts_arr[:, 0]), 0, w - 1))
                        y1 = int(np.clip(np.min(pts_arr[:, 1]), 0, h - 1))
                        x2 = int(np.clip(np.max(pts_arr[:, 0]), 0, w - 1))
                        y2 = int(np.clip(np.max(pts_arr[:, 1]), 0, h - 1))
                        if x2 - x1 >= 16 and y2 - y1 >= 16:
                            extra.append({
                                "class_name": "qr_code",
                                "confidence": 0.96,
                                "bbox": (x1, y1, x2, y2),
                            })
            except Exception:
                pass

        # 2. Phát hiện vật thể hình chữ nhật cầm tay (id_card, credit_card, receipt, document)
        if any(want(c) for c in ("id_card", "credit_card", "receipt", "document")):
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                edges = cv2.Canny(blurred, 55, 160)
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
                closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
                contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                frame_area = float(w * h)
                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    if area < frame_area * 0.02 or area > frame_area * 0.65:
                        continue
                    peri = cv2.arcLength(cnt, True)
                    approx = cv2.approxPolyDP(cnt, 0.035 * peri, True)
                    if not (4 <= len(approx) <= 6):
                        continue

                    rx, ry, rw, rh = cv2.boundingRect(approx)
                    if rw < 50 or rh < 35:
                        continue
                    rect_fill = area / float(rw * rh)
                    if rect_fill < 0.62:
                        continue

                    roi_edges = edges[ry:ry + rh, rx:rx + rw]
                    edge_density = float(np.count_nonzero(roi_edges)) / float(rw * rh)
                    if edge_density < 0.032:
                        continue

                    aspect = float(rw) / float(rh)
                    roi_bgr = frame[ry:ry + rh, rx:rx + rw]
                    hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
                    mean_sat = float(np.mean(hsv[:, :, 1]))
                    mean_val = float(np.mean(hsv[:, :, 2]))

                    detected_cls = None
                    # Thẻ ngang chuẩn ISO ID-1 (CCCD / Thẻ ngân hàng): tỷ lệ ~ 1.30 - 1.98
                    if 1.30 <= aspect <= 1.98 and area < frame_area * 0.35:
                        if mean_sat >= 45.0 and want("credit_card"):
                            detected_cls = "credit_card"
                        elif want("id_card"):
                            detected_cls = "id_card"
                        elif want("credit_card"):
                            detected_cls = "credit_card"
                    # Hóa đơn dọc (Receipt): hẹp và cao, nền sáng
                    elif 0.35 <= aspect <= 0.78 and mean_val >= 135.0 and want("receipt"):
                        detected_cls = "receipt"
                    # Tài liệu giấy (Document): diện tích lớn, nền sáng
                    elif 0.65 <= aspect <= 1.45 and area >= frame_area * 0.08 and mean_val >= 140.0 and want("document"):
                        detected_cls = "document"

                    if detected_cls is not None:
                        conf = min(0.94, round(0.55 + edge_density * 2.0, 2))
                        if conf >= self.confidence:
                            extra.append({
                                "class_name": detected_cls,
                                "confidence": conf,
                                "bbox": (rx, ry, rx + rw, ry + rh),
                            })
            except Exception:
                pass

        return extra
