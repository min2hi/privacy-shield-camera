import sys
from pathlib import Path

import cv2

# Thêm thư mục hiện tại vào python path để import được app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.pipeline import PrivacyPipeline
from app.utils.config_loader import ConfigLoader
from app.utils.console import safe_print


def main():
    safe_print("====================================================")
    safe_print("   PRIVACY SHIELD CAMERA - CLI SMOKE TEST RUNNER   ")
    safe_print("====================================================")
    
    # 1. Tải cấu hình
    try:
        config = ConfigLoader("configs/default.yaml")
        safe_print("Config loaded")
    except Exception as e:
        safe_print(f"Cannot load config: {e}")
        return

    # 2. Khởi tạo pipeline xử lý video
    try:
        pipeline = PrivacyPipeline(config)
        safe_print("CV pipeline initialized")
    except Exception as e:
        safe_print(f"Cannot initialize pipeline: {e}")
        return

    # 3. Mở webcam
    device_index = config.get("camera.device_index", 0)
    width = config.get("camera.width", 640)
    height = config.get("camera.height", 480)
    
    safe_print(f"Opening webcam index {device_index}")
    cap = cv2.VideoCapture(device_index)
    
    if not cap.isOpened():
        safe_print(f"Cannot open webcam index {device_index}")
        safe_print("Check the device or camera.device_index in configs/default.yaml")
        return
        
    # Cấu hình kích thước cho camera
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    safe_print("Webcam opened; starting stream")
    safe_print("Press q in the preview window to exit")

    # Lấy danh sách các class được cấu hình cần che từ YAML
    class_presets = config.get("model.class_mask_presets", {})
    selected_classes = list(class_presets.keys())
    safe_print(f"Requested protected classes: {selected_classes}")

    # 4. Vòng lặp đọc frame và xử lý
    while True:
        ret, frame = cap.read()
        if not ret:
            safe_print("Cannot read webcam frame")
            break

        # Lật gương hình ảnh theo chiều ngang 
        frame = cv2.flip(frame, 1)

        # Xử lý frame qua pipeline (chỉ detect các class nhạy cảm đã cấu hình)
        processed_frame, metrics = pipeline.process_frame(frame, selected_classes=selected_classes)

        # 5. Ghi đè thông tin hiển thị lên hình ảnh (UI overlays)
        fps = metrics.get("fps", 0.0)
        latency = metrics.get("latency_ms", 0.0)
        count = metrics.get("detected_count", 0)
        
        # Thêm background mờ phía sau text để dễ đọc hơn
        cv2.rectangle(processed_frame, (10, 10), (220, 90), (0, 0, 0), -1)
        
        # Vẽ các thông số lên góc trái trên cùng
        cv2.putText(
            processed_frame,
            f"FPS: {fps}",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1
        )
        cv2.putText(
            processed_frame,
            f"Latency: {latency} ms",
            (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1
        )
        cv2.putText(
            processed_frame,
            f"Detected: {count} objects",
            (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1
        )

        # 6. Hiển thị hình ảnh
        cv2.imshow("Privacy Shield Camera - Smoke Test", processed_frame)

        # Đọc phím bấm
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Giải phóng tài nguyên
    cap.release()
    cv2.destroyAllWindows()
    safe_print("CLI session ended")

if __name__ == "__main__":
    main()
