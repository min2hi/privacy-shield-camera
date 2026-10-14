import os

from ultralytics import YOLO

from app.core.model_bundle import ModelManifest
from app.utils.console import safe_print


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
        self.load_model()

    @property
    def supported_class_names(self):
        """Return the exact class names exposed by the loaded model."""
        if self.model is None:
            return set()
        if self.manifest is not None:
            return set(self.manifest.supported_privacy_classes)
        names = self.model.names
        values = names.values() if isinstance(names, dict) else names
        return {str(name) for name in values}

    def load_model(self):
        """
        Tải mô hình YOLOv8 từ đường dẫn cấu hình.
        Nếu không có sẵn tại đường dẫn, Ultralytics sẽ tự tải bản pretrained chính thức từ repo của họ.
        """
        # Đảm bảo thư mục cha của model tồn tại
        model_dir = os.path.dirname(self.model_path)
        if model_dir and not os.path.exists(model_dir):
            os.makedirs(model_dir, exist_ok=True)
            
        safe_print(f"Detector: loading YOLO model from {self.model_path}")
        if self.manifest is not None:
            self.manifest.validate_asset(self.model_path)
        self.model = YOLO(self.model_path)
        if self.manifest is not None:
            names = self.model.names
            runtime_names = names.values() if isinstance(names, dict) else names
            self.manifest.validate_runtime_classes(runtime_names)
        safe_print("Detector: model loaded")

    def detect(self, frame, selected_classes=None):
        """
        Chạy phát hiện đối tượng trên một frame ảnh.
        selected_classes: Danh sách tên các class cần lọc. Nếu None, nhận diện tất cả các class.
        Trả về: Danh sách các dict [{ 'class_name': ..., 'confidence': ..., 'bbox': (x1, y1, x2, y2) }]
        """
        if self.model is None:
            return []

        results = self.model.predict(
            source=frame,
            conf=self.confidence,
            iou=self.iou,
            device=self.device,
            verbose=False,
            imgsz=self.image_size
        )

        detections = []
        if len(results) == 0:
            return detections

        result = results[0]
        boxes = result.boxes

        for box in boxes:
            cls_id = int(box.cls[0].item())
            class_name = str(self.model.names[cls_id])
            
            # Lọc các class mong muốn (nếu được yêu cầu)
            if selected_classes is not None and class_name not in selected_classes:
                continue

            confidence = float(box.conf[0].item())
            # Tọa độ bbox: x1, y1, x2, y2
            xyxy = box.xyxy[0].cpu().numpy().reshape(-1)
            x1, y1, x2, y2 = map(int, xyxy)

            detections.append({
                "class_name": class_name,
                "confidence": confidence,
                "bbox": (x1, y1, x2, y2)
            })

        return detections
