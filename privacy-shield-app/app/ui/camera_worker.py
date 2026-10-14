"""
camera_worker.py — Luồng chạy camera nền (QThread) cho Privacy Shield App.
"""

import threading
import time

import cv2
from app.core.virtual_camera import VirtualCameraOutput
from app.utils.console import safe_print
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage


class CameraWorker(QThread):
    # Signal truyền ảnh đã xử lý và metrics thống kê về UI Thread
    frame_ready = Signal(QImage, dict)
    enroll_result = Signal(bool, str)  # Signal báo kết quả đăng ký khuôn mặt mẫu (thành công, thông báo)
    camera_error = Signal(str)
    
    def __init__(
        self,
        pipeline,
        device_index=0,
        selected_classes=None,
        virtual_output=None,
        capture_factory=None,
        sleep_fn=None,
    ):
        super().__init__()
        self.pipeline = pipeline
        self.device_index = device_index
        self.selected_classes = selected_classes if selected_classes is not None else []
        self.running = True
        
        # Các trạng thái điều khiển động từ giao diện
        self.safe_mode_active = True  # Bật/tắt che đối tượng nhạy cảm
        self.override_mask_mode = None  # Nếu None thì dùng theo Preset rủi ro, ngược lại force tất cả về 1 kiểu che
        self.enroll_pose_index = -1  # Chỉ số góc mặt đang yêu cầu quét (-1: rảnh, 0: thẳng, 1: trái, 2: phải)
        self.enroll_start_time = 0.0  # Thời điểm bắt đầu yêu cầu đăng ký mặt mẫu
        self.virtual_output = virtual_output
        self.capture_factory = capture_factory or cv2.VideoCapture
        self.sleep_fn = sleep_fn or time.sleep
        self._capture = None
        self._config_lock = threading.Lock()
        
    def request_pose_enrollment(self, pose_index):
        """Kích hoạt yêu cầu quét góc mặt mẫu cụ thể (0: nhìn thẳng, 1: nghiêng trái, 2: nghiêng phải)."""
        self.enroll_pose_index = pose_index
        self.enroll_start_time = time.time()

    def update_config(self, safe_mode=None, override_mask=None, selected_classes=None):
        """Thread-safe: cập nhật cấu hình từ UI thread."""
        with self._config_lock:
            if safe_mode is not None:
                self.safe_mode_active = safe_mode
            if override_mask is not None:
                self.override_mask_mode = override_mask
            if selected_classes is not None:
                self.selected_classes = list(selected_classes)

    def _get_config(self):
        """Thread-safe: đọc cấu hình hiện tại trong worker thread."""
        with self._config_lock:
            return (
                self.safe_mode_active,
                self.override_mask_mode,
                list(self.selected_classes),
            )
        
    def run(self):
        safe_print(f"CameraWorker: opening camera index {self.device_index}")
        cap = self.capture_factory(self.device_index)
        self._capture = cap
        
        # Thiết lập kích thước mặc định cho camera để tối ưu hóa CPU
        width = self.pipeline.config.get("camera.width", 640)
        height = self.pipeline.config.get("camera.height", 480)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        requested_fps = self.pipeline.config.get("camera.fps", 30)
        max_read_failures = self.pipeline.config.get("camera.max_read_failures", 30)
        retry_delay = (
            self.pipeline.config.get("camera.read_retry_delay_ms", 30) / 1000.0
        )
        cap.set(cv2.CAP_PROP_FPS, requested_fps)

        if self.virtual_output is None and self.pipeline.config.get(
            "output.virtual_camera.enabled", False
        ):
            self.virtual_output = VirtualCameraOutput(width, height, requested_fps)

        if self.virtual_output is not None:
            try:
                self.virtual_output.open()
            except Exception as exc:
                self.camera_error.emit(f"Không mở được virtual camera: {exc}")
                self.virtual_output = None
        
        if not cap.isOpened():
            safe_print(f"CameraWorker: cannot open camera index {self.device_index}")
            # Gửi tín hiệu báo lỗi về UI
            self.running = False
            self.camera_error.emit(f"Không mở được camera index {self.device_index}")

        consecutive_read_failures = 0
        last_frame_time = time.perf_counter()
            
        while self.running:
            ret, frame = cap.read()
            if not ret:
                consecutive_read_failures += 1
                if consecutive_read_failures >= max_read_failures:
                    fallback = self.pipeline.privacy_screen(
                        self._blank_frame(width, height), "CAMERA DISCONNECTED"
                    )
                    self._emit_frame(
                        fallback,
                        {
                            "fps": 0.0,
                            "latency_ms": 0.0,
                            "detected_count": 0,
                            "detections": [],
                            "state": "error",
                            "error": "camera disconnected",
                        },
                    )
                    self.camera_error.emit("Camera mất kết nối")
                    break
                self.sleep_fn(retry_delay)
                continue
            consecutive_read_failures = 0
            
            # 1. Lật gương hình ảnh ngang theo chiều tự nhiên (Mirror)
            frame = cv2.flip(frame, 1)
            
            # Xử lý yêu cầu quét góc mặt mẫu (Multi-Pose Enrollment)
            if self.enroll_pose_index >= 0:
                faces = self.pipeline.face_recognizer.detect_faces(frame)
                if faces:
                    # Lấy khuôn mặt lớn nhất ở gần camera nhất
                    best_face = max(faces, key=lambda f: f["bbox"][2] * f["bbox"][3])
                    xmin, ymin, w, h = best_face["bbox"]
                    
                    if w >= 100 and h >= 100:
                        # Xác định góc nghiêng mặt thực tế bằng landmark
                        detected_pose = self.pipeline.face_recognizer.estimate_head_pose(best_face["face_object"])
                        if detected_pose != self.enroll_pose_index:
                            pose_names = {0: "Nhìn Thẳng", 1: "Nghiêng Trái", 2: "Nghiêng Phải"}
                            detected_names = {-2: "Cúi/Ngửa đầu", 0: "Nhìn Thẳng", 1: "Nghiêng Trái", 2: "Nghiêng Phải"}
                            # Nếu quá 5 giây không đúng góc mặt, kích hoạt timeout
                            if time.time() - self.enroll_start_time > 5.0:
                                idx = self.enroll_pose_index
                                self.enroll_pose_index = -1
                                self.enroll_result.emit(False, f"Đăng ký thất bại: Phát hiện tư thế {detected_names.get(detected_pose, 'Không xác định')} (Yêu cầu: {pose_names[idx]}). Hãy thực hiện đúng hướng dẫn!")
                        else:
                            success = self.pipeline.face_recognizer.register_face_pose(frame, best_face["bbox"], self.enroll_pose_index)
                            if success:
                                # Nếu đây là góc mặt cuối cùng (index 2), thực hiện lưu trữ xuống đĩa
                                if self.enroll_pose_index == 2:
                                    self.pipeline.face_recognizer.save_registered_faces()
                                
                                idx = self.enroll_pose_index
                                self.enroll_pose_index = -1  # Reset trạng thái quét
                                self.enroll_result.emit(True, f"Đã quét thành công góc mặt {idx + 1}/3!")
                            else:
                                self.enroll_pose_index = -1
                                self.enroll_result.emit(False, "Đăng ký thất bại: Lỗi trích xuất vector đặc trưng.")
                    else:
                        if time.time() - self.enroll_start_time > 5.0:
                            self.enroll_pose_index = -1
                            self.enroll_result.emit(False, "Đăng ký thất bại: Hãy di chuyển khuôn mặt lại gần camera hơn!")
                else:
                    if time.time() - self.enroll_start_time > 4.0:
                        self.enroll_pose_index = -1
                        self.enroll_result.emit(False, "Đăng ký thất bại: Không tìm thấy khuôn mặt rõ ràng trong khung hình!")
            
            # 2. Xử lý qua pipeline (thread-safe config read)
            safe_mode, override_mask, classes = self._get_config()
            if safe_mode:
                # Truyền cấu hình override vào masker của pipeline trước khi xử lý
                self.pipeline.masker.override_mask_mode = override_mask
                
                # Thực hiện suy luận và che các đối tượng nhạy cảm
                processed_frame, metrics = self.pipeline.process_frame(
                    frame, 
                    selected_classes=classes
                )
            else:
                # Paused remains fail-closed: never expose raw pixels.
                processed_frame = self.pipeline.privacy_screen(frame, "PROTECTION PAUSED")
                now = time.perf_counter()
                elapsed = now - last_frame_time
                last_frame_time = now
                metrics = {
                    "fps": round(1.0 / elapsed, 1) if elapsed > 0 else 0.0,
                    "latency_ms": 0.0,
                    "detected_count": 0,
                    "detections": [],
                    "state": "paused_safe",
                }

            if self.virtual_output is not None:
                try:
                    self.virtual_output.send_bgr(processed_frame)
                except Exception as exc:
                    metrics["virtual_camera_error"] = str(exc)
                    self.camera_error.emit(f"Virtual camera lỗi: {exc}")
                    self.virtual_output.close()
                    self.virtual_output = None

            self._emit_frame(processed_frame, metrics)

            # Nhịp thở cho thread
            self.sleep_fn(0.001)

        cap.release()
        self._capture = None
        if self.virtual_output is not None:
            self.virtual_output.close()
        self.pipeline.reset_tracking()
        safe_print("CameraWorker: capture and output resources released")

    @staticmethod
    def _blank_frame(width, height):
        import numpy as np

        return np.zeros((height, width, 3), dtype=np.uint8)

    def _emit_frame(self, processed_frame, metrics):
        """Emit an owned QImage so queued delivery never references a dead NumPy buffer."""
        rgb_image = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        self.frame_ready.emit(q_img, metrics)

    def stop(self):
        """Dừng luồng an toàn — chỉ set flag, để run() tự release hardware."""
        self.running = False
        if self.isRunning() and not self.wait(5000):
            self.camera_error.emit("Camera worker không dừng trong thời gian cho phép")
