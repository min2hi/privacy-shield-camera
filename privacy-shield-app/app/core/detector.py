from __future__ import annotations

import os
from collections.abc import Collection
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from ultralytics import YOLO

from app.core.model_bundle import ModelManifest
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

HYBRID_PRIVACY_CLASSES: frozenset[str] = frozenset({
    "cell phone",
    "id_card",
    "credit_card",
    "qr_code",
    "receipt",
    "smartphone_screen",
    "document",
})


class Detector:
    model_path: str
    confidence: float
    iou: float
    device: str
    image_size: int
    manifest: ModelManifest | None
    model: Any
    _qr_detector: cv2.QRCodeDetector | None

    def __init__(
        self,
        model_path: str | Path = "models/yolov8n.pt",
        confidence: float = 0.25,
        iou: float = 0.45,
        device: str = "cpu",
        image_size: int = 640,
        manifest_path: str | Path | None = None,
    ) -> None:
        self.model_path = str(model_path)
        self.confidence = confidence
        self.iou = iou
        self.device = device
        self.image_size = image_size
        self.manifest = ModelManifest.load(manifest_path) if manifest_path else None
        self.model = None
        self._qr_detector = cv2.QRCodeDetector()
        self.load_model()

    @property
    def supported_class_names(self) -> set[str]:
        """Return the exact class names exposed by the loaded model + hybrid CV pipeline."""
        if self.model is None:
            return set()
        if self.manifest is not None:
            return set(self.manifest.supported_privacy_classes)
        names = self.model.names
        values = names.values() if isinstance(names, dict) else names
        return {str(name) for name in values} | set(HYBRID_PRIVACY_CLASSES)

    def load_model(self) -> None:
        """
        Tải mô hình YOLOv8 từ đường dẫn cấu hình.
        Nếu không có sẵn tại đường dẫn, Ultralytics sẽ tự tải bản pretrained chính thức từ repo của họ.
        """
        model_dir = os.path.dirname(self.model_path)
        if model_dir and not os.path.exists(model_dir):
            os.makedirs(model_dir, exist_ok=True)

        logger.info("Detector: loading YOLO model from %s", self.model_path)
        if self.manifest is not None:
            self.manifest.validate_asset(self.model_path)
        self.model = YOLO(self.model_path)
        names = self.model.names
        if isinstance(names, dict):
            self._name_to_id: dict[str, int] = {str(v): int(k) for k, v in names.items()}
            runtime_names = {str(v) for v in names.values()}
        else:
            self._name_to_id = {str(v): int(i) for i, v in enumerate(names)}
            runtime_names = {str(v) for v in names}
        if self.manifest is not None:
            runtime_names |= set(HYBRID_PRIVACY_CLASSES)
            self.manifest.validate_runtime_classes(runtime_names)
        self._qr_step = 0
        self._last_qr_detections: list[dict[str, Any]] = []
        logger.info("Detector: model loaded")

    def detect(
        self, frame: np.ndarray | None, selected_classes: Collection[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Chạy phát hiện đối tượng trên một frame ảnh (kết hợp YOLOv8 + OpenCV QR/Card/Document).
        selected_classes: Danh sách tên các class cần lọc. Nếu None, nhận diện tất cả các class.
        Trả về: Danh sách các dict [{ 'class_name': ..., 'confidence': ..., 'bbox': (x1, y1, x2, y2) }]
        """
        if self.model is None or frame is None or getattr(frame, "size", 0) == 0:
            return []

        name_to_id = getattr(self, "_name_to_id", None)
        yolo_classes: list[int] | None = None
        run_yolo = True
        if selected_classes is not None and name_to_id:
            yolo_classes = [name_to_id[c] for c in selected_classes if c in name_to_id]
            if len(selected_classes) > 0 and not yolo_classes:
                run_yolo = False

        detections: list[dict[str, Any]] = []
        if run_yolo:
            predict_kwargs: dict[str, Any] = {
                "source": frame,
                "conf": self.confidence,
                "iou": self.iou,
                "device": self.device,
                "verbose": False,
                "imgsz": self.image_size,
            }
            if yolo_classes:
                predict_kwargs["classes"] = yolo_classes

            results = self.model.predict(**predict_kwargs)
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

    def _detect_qr_and_cards(
        self, frame: np.ndarray, selected_classes: Collection[str] | None = None
    ) -> list[dict[str, Any]]:
        """Phát hiện thời gian thực mã QR và các vật thể dạng thẻ/hóa đơn/tài liệu.
        Tối ưu hiệu năng: xử lý trên ảnh thu nhỏ 320px dùng chung kênh xám (grayscale),
        giảm thời gian từ ~13ms xuống ~1.5ms mỗi frame.
        """
        extra: list[dict[str, Any]] = []
        if not isinstance(frame, np.ndarray) or frame.ndim != 3:
            return extra
        h, w = frame.shape[:2]
        if h < 40 or w < 40:
            return extra
        # Bỏ qua frame đen hoàn toàn (như trong unit test np.zeros) để tránh tốn CPU
        if not np.any(frame):
            return extra

        def want(cls_name: str) -> bool:
            return selected_classes is None or cls_name in selected_classes

        want_qr = want("qr_code")
        want_cards = any(want(c) for c in ("id_card", "credit_card", "receipt", "document"))
        if not want_qr and not want_cards:
            return extra

        # Thu nhỏ về tối đa 320px để tăng tốc Canny / Morphology / QR
        max_dim = max(w, h)
        if max_dim > 320:
            scale = 320.0 / float(max_dim)
            sw = max(40, int(round(w * scale)))
            sh = max(40, int(round(h * scale)))
            small_bgr = cv2.resize(frame, (sw, sh), interpolation=cv2.INTER_LINEAR)
            inv_scale_x = float(w) / float(sw)
            inv_scale_y = float(h) / float(sh)
        else:
            scale = 1.0
            sw, sh = w, h
            small_bgr = frame
            inv_scale_x = 1.0
            inv_scale_y = 1.0

        small_gray = cv2.cvtColor(small_bgr, cv2.COLOR_BGR2GRAY)

        # 1. Phát hiện mã QR bằng OpenCV QRCodeDetector trên ảnh xám thu nhỏ
        if want_qr:
            qr_step = getattr(self, "_qr_step", 0)
            self._qr_step = qr_step + 1
            if qr_step % 2 == 0:
                qr_found: list[dict[str, Any]] = []
                try:
                    qr_det = getattr(self, "_qr_detector", None)
                    if qr_det is None:
                        qr_det = cv2.QRCodeDetector()
                        self._qr_detector = qr_det
                    ok, points = qr_det.detect(small_gray)
                    if ok and points is not None:
                        pts_arr = np.array(points, dtype=np.float32).reshape(-1, 2)
                        qx1 = int(np.clip(np.min(pts_arr[:, 0]), 0, sw - 1))
                        qy1 = int(np.clip(np.min(pts_arr[:, 1]), 0, sh - 1))
                        qx2 = int(np.clip(np.max(pts_arr[:, 0]), 0, sw - 1))
                        qy2 = int(np.clip(np.max(pts_arr[:, 1]), 0, sh - 1))
                        qw = qx2 - qx1
                        qh = qy2 - qy1
                        if (
                            qw >= 16
                            and qh >= 16
                            and 0.55 <= (float(qw) / float(qh)) <= 1.80
                            and (qw * qh) < (sw * sh * 0.30)
                        ):
                            qr_roi = small_gray[qy1:qy2, qx1:qx2]
                            if qr_roi.size > 0 and float(np.std(qr_roi)) >= 28.0:
                                x1 = int(np.clip(qx1 * inv_scale_x, 0, w - 1))
                                y1 = int(np.clip(qy1 * inv_scale_y, 0, h - 1))
                                x2 = int(np.clip(qx2 * inv_scale_x, 0, w - 1))
                                y2 = int(np.clip(qy2 * inv_scale_y, 0, h - 1))
                                qr_found.append({
                                    "class_name": "qr_code",
                                    "confidence": 0.96,
                                    "bbox": (x1, y1, x2, y2),
                                })
                except Exception:
                    logger.warning("Heuristic QR detection failed", exc_info=True)
                self._last_qr_detections = qr_found
                extra.extend(qr_found)
            else:
                extra.extend(getattr(self, "_last_qr_detections", []))

        # 2. Phát hiện vật thể hình chữ nhật cầm tay (id_card, credit_card, receipt, document)
        # Cân bằng độ nhạy khi cầm nghiêng trên tay (cho phép góc phối cảnh 3D nhẹ) nhưng vẫn
        # chặn tuyệt đối các đường viền chạm biên màn hình hoặc chứa sắc tố da mặt người.
        if want_cards:
            try:
                blurred = cv2.GaussianBlur(small_gray, (5, 5), 0)
                edges = cv2.Canny(blurred, 50, 155)
                k_size = 3 if scale < 1.0 else 5
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k_size, k_size))
                closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
                contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                frame_area = float(sw * sh)
                min_w = max(20, int(48 * scale))
                min_h = max(15, int(32 * scale))
                margin_x = max(4, int(sw * 0.015))
                margin_y = max(4, int(sh * 0.015))

                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    # Thẻ/giấy tờ cầm tay chiếm từ 1.6% đến 34% diện tích khung hình
                    if area < frame_area * 0.016 or area > frame_area * 0.34:
                        continue
                    peri = cv2.arcLength(cnt, True)
                    approx = cv2.approxPolyDP(cnt, 0.030 * peri, True)
                    # Cho phép 4-5 đỉnh lồi (khi ngón tay cầm che nhẹ 1 góc thẻ)
                    if not (4 <= len(approx) <= 5) or not cv2.isContourConvex(approx):
                        continue

                    rx, ry, rw, rh = cv2.boundingRect(approx)
                    if rw < min_w or rh < min_h:
                        continue
                    # Loại bỏ các vùng chạm sát biên khung hình (tường, trần nhà, cơ thể người)
                    if (
                        rx <= margin_x
                        or ry <= margin_y
                        or (rx + rw) >= (sw - margin_x)
                        or (ry + rh) >= (sh - margin_y)
                    ):
                        continue

                    # Kiểm tra độ lấp đầy hình chữ nhật xoay (minAreaRect)
                    (_, _), (maw, mah), _ = cv2.minAreaRect(cnt)
                    min_rect_area = float(maw * mah)
                    if min_rect_area <= 0 or (area / min_rect_area) < 0.78:
                        continue
                    rect_fill = area / float(rw * rh)
                    if rect_fill < 0.68:
                        continue

                    if len(approx) == 4:
                        pts = approx.reshape(4, 2).astype(np.float32)
                        max_cos = 0.0
                        for i in range(4):
                            p0 = pts[i]
                            p1 = pts[(i + 1) % 4]
                            p2 = pts[(i + 2) % 4]
                            v1 = p0 - p1
                            v2 = p2 - p1
                            denom = float(np.linalg.norm(v1) * np.linalg.norm(v2)) + 1e-6
                            cos_angle = abs(float(np.dot(v1, v2)) / denom)
                            if cos_angle > max_cos:
                                max_cos = cos_angle
                        # Cho phép góc nghiêng phối cảnh 3D khi cầm thẻ trên tay (|cos| <= 0.32 ~ 90°±18°)
                        if max_cos > 0.32:
                            continue

                    # Kiểm tra mật độ nét chữ/chi tiết bên trong lòng thẻ (tránh nhận nhầm mảng tường trắng trơn)
                    pad_x = max(2, int(rw * 0.14))
                    pad_y = max(2, int(rh * 0.14))
                    inner_edges = edges[ry + pad_y : ry + rh - pad_y, rx + pad_x : rx + rw - pad_x]
                    if inner_edges.size == 0:
                        continue
                    inner_edge_density = float(np.count_nonzero(inner_edges)) / float(
                        inner_edges.size
                    )
                    if inner_edge_density < 0.016 or inner_edge_density > 0.32:
                        continue

                    roi_bgr = small_bgr[ry : ry + rh, rx : rx + rw]
                    inner_bgr = roi_bgr[pad_y : rh - pad_y, pad_x : rw - pad_x]
                    if inner_bgr.size == 0:
                        continue

                    # Loại bỏ tuyệt đối nếu vùng bên trong chứa sắc tố da người (YCrCb skin cluster)
                    ycrcb = cv2.cvtColor(inner_bgr, cv2.COLOR_BGR2YCrCb)
                    cr = ycrcb[:, :, 1]
                    cb = ycrcb[:, :, 2]
                    skin_mask = (cr >= 135) & (cr <= 172) & (cb >= 77) & (cb <= 127)
                    skin_ratio = float(np.count_nonzero(skin_mask)) / float(cr.size)
                    if skin_ratio > 0.15:
                        continue

                    hsv = cv2.cvtColor(inner_bgr, cv2.COLOR_BGR2HSV)
                    mean_sat = float(np.mean(hsv[:, :, 1]))
                    mean_val = float(np.mean(hsv[:, :, 2]))
                    p75_val = float(np.percentile(hsv[:, :, 2], 75))
                    # Bề mặt thẻ/giấy có nền sáng
                    if p75_val < 125.0:
                        continue

                    aspect = float(rw) / float(rh)
                    detected_cls = None
                    # Thẻ ngang chuẩn ISO ID-1 (CCCD / Thẻ ngân hàng): tỷ lệ ~ 1.25 - 1.95
                    if 1.25 <= aspect <= 1.95 and area < frame_area * 0.28:
                        if mean_sat >= 42.0 and want("credit_card"):
                            detected_cls = "credit_card"
                        elif want("id_card"):
                            detected_cls = "id_card"
                        elif want("credit_card"):
                            detected_cls = "credit_card"
                    # Hóa đơn dọc (Receipt): hẹp và cao, nền giấy sáng
                    elif (
                        0.36 <= aspect <= 0.75
                        and mean_val >= 145.0
                        and mean_sat <= 55.0
                        and want("receipt")
                    ):
                        detected_cls = "receipt"
                    # Tài liệu giấy (Document): trang giấy sáng
                    elif (
                        0.68 <= aspect <= 1.40
                        and area >= frame_area * 0.05
                        and mean_val >= 145.0
                        and mean_sat <= 55.0
                        and want("document")
                    ):
                        detected_cls = "document"

                    if detected_cls is not None:
                        conf = min(0.92, round(0.68 + inner_edge_density * 2.2, 2))
                        effective_thresh = min(float(self.confidence), 0.55)
                        if conf >= effective_thresh:
                            x1 = int(round(rx * inv_scale_x))
                            y1 = int(round(ry * inv_scale_y))
                            x2 = int(round((rx + rw) * inv_scale_x))
                            y2 = int(round((ry + rh) * inv_scale_y))
                            extra.append({
                                "class_name": detected_cls,
                                "confidence": conf,
                                "bbox": (x1, y1, x2, y2),
                            })
            except Exception:
                logger.warning("Heuristic card/document detection failed", exc_info=True)

        return extra
