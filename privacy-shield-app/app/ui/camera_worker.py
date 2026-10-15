"""
camera_worker.py — Luồng chạy camera nền (QThread) cho Privacy Shield App.
"""

import math
import os
import threading
import time

import cv2
import numpy as np
from app.core.virtual_camera import VirtualCameraOutput
from app.utils.logging_config import get_logger
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

logger = get_logger(__name__)

# Sentinel object to distinguish "no change" from "set to None"
_UNSET = object()


class DemoVideoCapture:
    """Bộ phát khung hình mô phỏng trực quan (30 FPS) chứa CCCD, Thẻ Ngân hàng, QR Code, Hóa đơn để demo trực tiếp trên giao diện."""

    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height
        self._opened = True
        self._tick = 0
        self._last_read_time = 0.0

    def isOpened(self):
        return self._opened

    def set(self, prop, value):
        if prop == cv2.CAP_PROP_FRAME_WIDTH:
            self.width = int(value)
        elif prop == cv2.CAP_PROP_FRAME_HEIGHT:
            self.height = int(value)
        return True

    def read(self):
        if not self._opened:
            return False, None

        # Điều nhịp thông minh (Adaptive Frame Pacing): trừ thời gian xử lý AI của frame trước
        # để giữ chuẩn 30 FPS thay vì sleep cứng 30ms gây cộng dồn độ trễ.
        now = time.perf_counter()
        if self._last_read_time > 0.0:
            elapsed = now - self._last_read_time
            target_interval = 1.0 / 30.0
            if elapsed < target_interval:
                time.sleep(target_interval - elapsed)
        self._last_read_time = time.perf_counter()

        self._tick += 1
        t = self._tick * 0.06
        w, h = self.width, self.height
        frame = np.full((h, w, 3), (34, 38, 46), dtype=np.uint8)

        # Nền phòng làm việc giả lập nhẹ nhàng
        cv2.rectangle(frame, (0, 0), (w, int(h * 0.72)), (44, 50, 62), -1)
        cv2.rectangle(frame, (0, int(h * 0.72)), (w, h), (28, 31, 38), -1)

        dx = int(math.sin(t) * 10)
        dy = int(math.cos(t * 0.8) * 6)

        # 1. Thẻ Căn Cước Công Dân giả lập (id_card: tỷ lệ ~ 1.58, độ bão hòa màu thấp)
        ix1, iy1 = 36 + dx, 55 + dy
        ix2, iy2 = ix1 + 210, iy1 + 132
        cv2.rectangle(frame, (ix1, iy1), (ix2, iy2), (232, 236, 240), -1)
        cv2.rectangle(frame, (ix1, iy1), (ix2, iy2), (90, 100, 115), 2)
        cv2.rectangle(frame, (ix1 + 12, iy1 + 34), (ix1 + 64, iy1 + 108), (160, 165, 175), -1)
        cv2.putText(frame, "CAN CUOC CONG DAN", (ix1 + 14, iy1 + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (40, 50, 70), 2)
        cv2.putText(frame, "ID: 048204001234", (ix1 + 74, iy1 + 52), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (25, 25, 25), 1)
        cv2.putText(frame, "NGUYEN VAN A", (ix1 + 74, iy1 + 76), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (35, 35, 35), 1)
        cv2.putText(frame, "DOB: 15/08/2004", (ix1 + 74, iy1 + 100), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (50, 50, 50), 1)

        # 2. Thẻ Ngân Hàng giả lập (credit_card: tỷ lệ ~ 1.58, độ bão hòa màu cao)
        cx1, cy1 = 38 + dx, 235 - dy
        cx2, cy2 = cx1 + 215, cy1 + 135
        cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (185, 95, 20), -1)
        cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (240, 180, 70), 2)
        cv2.rectangle(frame, (cx1 + 18, cy1 + 42), (cx1 + 52, cy1 + 68), (60, 215, 255), -1)
        cv2.putText(frame, "BANK PLATINUM VISA", (cx1 + 16, cy1 + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 245, 220), 2)
        cv2.putText(frame, "4532 8910 2345 6789", (cx1 + 16, cy1 + 94), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 2)
        cv2.putText(frame, "VALID 08/29  CVV 889", (cx1 + 16, cy1 + 118), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (240, 230, 210), 1)

        # 3. Hóa đơn mua hàng giả lập (receipt: hẹp & cao, nền sáng)
        rx1, ry1 = 445 - dx, 55 + dy
        rx2, ry2 = rx1 + 145, ry1 + 265
        cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (245, 245, 245), -1)
        cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (110, 110, 110), 2)
        cv2.putText(frame, "HOA DON THANH TOAN", (rx1 + 8, ry1 + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.37, (20, 20, 20), 1)
        for line_idx in range(7):
            ly = ry1 + 52 + line_idx * 26
            cv2.line(frame, (rx1 + 12, ly), (rx2 - 14, ly), (60, 60, 60), 2)
        cv2.putText(frame, "TONG: 1.250.000 VND", (rx1 + 10, ry2 - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (10, 10, 10), 1)

        # Lật ngược trước khi CameraWorker cv2.flip(frame, 1) để chữ xuôi chiều
        frame = cv2.flip(frame, 1)
        return True, frame

    def release(self):
        self._opened = False


class CameraWorker(QThread):
    # Signal truyền ảnh đã xử lý và metrics thống kê về UI Thread
    frame_ready = Signal(QImage, dict)
    enroll_result = Signal(bool, str)  # Signal báo kết quả đăng ký khuôn mặt mẫu (thành công, thông báo)
    camera_error = Signal(str)
    face_delete_result = Signal(bool)  # Signal báo kết quả xóa mẫu mặt (đã xóa hay không)
    face_status_update = Signal(int)   # Signal cập nhật số lượng embeddings đã đăng ký


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
        self.capture_factory = capture_factory or self._default_capture_factory
        self.sleep_fn = sleep_fn or time.sleep
        self._capture = None
        self._config_lock = threading.Lock()
        self._pipeline_lock = threading.Lock()
        self._infer_lock = threading.Lock()
        self._infer_event = threading.Event()
        self._infer_stop = False
        self._latest_infer_job = None
        self._async_state = None

    @staticmethod
    def _default_capture_factory(device_index):
        if device_index == 2:
            return DemoVideoCapture()
        if os.name == "nt":
            # Ưu tiên DirectShow trên Windows để giảm độ trễ buffer phần cứng (MSMF thường trễ 4-5 frame)
            cap = cv2.VideoCapture(device_index, cv2.CAP_DSHOW)
            if cap.isOpened():
                return cap
            cap.release()
        return cv2.VideoCapture(device_index)

    def request_pose_enrollment(self, pose_index):
        """Kích hoạt yêu cầu quét góc mặt mẫu cụ thể (0: nhìn thẳng, 1: trái, 2: phải)."""
        with self._config_lock:
            self.enroll_pose_index = pose_index
            self.enroll_start_time = time.time()

    def update_config(self, safe_mode=None, override_mask=_UNSET, selected_classes=None,
                      confidence=None, mask_owner_face=None, mask_strangers_face=None,
                      virtual_camera_enabled=None,
                      default_mask_mode=None, expand_ratio=None,
                      hold_frames=None, scheduler_enabled=None,
                      scheduler_skip_ratio=None, reset_tracking=None):
        """Thread-safe: cập nhật cấu hình từ UI thread."""
        with self._config_lock:
            if safe_mode is not None:
                self.safe_mode_active = safe_mode
            if override_mask is not _UNSET:
                self.override_mask_mode = override_mask
            if selected_classes is not None:
                self.selected_classes = list(selected_classes)
            if confidence is not None:
                self._pending_confidence = confidence
            if mask_owner_face is not None:
                self._pending_mask_owner = mask_owner_face
            if mask_strangers_face is not None:
                self._pending_mask_stranger = mask_strangers_face
            if virtual_camera_enabled is not None:
                self._pending_vcam = virtual_camera_enabled
            if default_mask_mode is not None:
                self._pending_default_mask_mode = default_mask_mode
            if expand_ratio is not None:
                self._pending_expand_ratio = expand_ratio
            if hold_frames is not None:
                self._pending_hold_frames = hold_frames
            if scheduler_enabled is not None:
                self._pending_scheduler_enabled = scheduler_enabled
            if scheduler_skip_ratio is not None:
                self._pending_scheduler_skip_ratio = scheduler_skip_ratio
            if reset_tracking is not None:
                self._pending_reset_tracking = bool(reset_tracking)

    def _get_config(self):
        """Thread-safe: đọc cấu hình hiện tại trong worker thread."""
        with self._config_lock:
            config = (
                self.safe_mode_active,
                self.override_mask_mode,
                list(self.selected_classes),
            )
            pending_conf = getattr(self, "_pending_confidence", None)
            pending_owner = getattr(self, "_pending_mask_owner", None)
            pending_stranger = getattr(self, "_pending_mask_stranger", None)
            pending_vcam = getattr(self, "_pending_vcam", None)
            pending_default_mask = getattr(self, "_pending_default_mask_mode", None)
            pending_expand = getattr(self, "_pending_expand_ratio", None)
            pending_hold = getattr(self, "_pending_hold_frames", None)
            pending_sched_en = getattr(self, "_pending_scheduler_enabled", None)
            pending_sched_skip = getattr(self, "_pending_scheduler_skip_ratio", None)
            pending_reset_tracking = getattr(self, "_pending_reset_tracking", False)
            pending_face_delete = getattr(self, "_pending_face_delete", False)
            pending_face_save = getattr(self, "_pending_face_save", False)
            # Clear pending
            self._pending_confidence = None
            self._pending_mask_owner = None
            self._pending_mask_stranger = None
            self._pending_vcam = None
            self._pending_default_mask_mode = None
            self._pending_expand_ratio = None
            self._pending_hold_frames = None
            self._pending_scheduler_enabled = None
            self._pending_scheduler_skip_ratio = None
            self._pending_reset_tracking = False
            self._pending_face_delete = False
            self._pending_face_save = False

        has_pipeline_mutation = any([
            pending_conf is not None,
            pending_owner is not None,
            pending_stranger is not None,
            pending_default_mask is not None,
            pending_expand is not None,
            pending_hold is not None,
            pending_sched_en is not None,
            pending_sched_skip is not None,
            pending_reset_tracking,
            pending_face_delete,
            pending_face_save,
        ])
        if has_pipeline_mutation:
            with self._pipeline_lock:
                if pending_conf is not None:
                    self.pipeline.detector.confidence = pending_conf
                if pending_owner is not None:
                    self.pipeline.mask_owner_face = pending_owner
                if pending_stranger is not None:
                    self.pipeline.mask_strangers_face = pending_stranger
                if pending_default_mask is not None and hasattr(self.pipeline, "masker"):
                    self.pipeline.masker.default_mask_mode = pending_default_mask
                if pending_expand is not None and hasattr(self.pipeline, "masker"):
                    self.pipeline.masker.expand_ratio = pending_expand
                if pending_hold is not None and hasattr(self.pipeline, "smoothing"):
                    self.pipeline.smoothing.hold_frames = pending_hold
                if pending_sched_en is not None and hasattr(self.pipeline, "scheduler"):
                    self.pipeline.scheduler.enabled = pending_sched_en
                if pending_sched_skip is not None and hasattr(self.pipeline, "scheduler"):
                    self.pipeline.scheduler.skip_ratio = max(1, pending_sched_skip)
                if pending_reset_tracking and hasattr(self.pipeline, "reset_tracking"):
                    self.pipeline.reset_tracking()
                    with self._infer_lock:
                        self._async_state = None
                if pending_face_delete:
                    removed = self.pipeline.face_recognizer.delete_registered_faces()
                    self.face_delete_result.emit(removed)
                if pending_face_save:
                    self.pipeline.face_recognizer.save_registered_faces()
                if any([
                    pending_owner is not None,
                    pending_stranger is not None,
                    pending_face_delete,
                    pending_face_save,
                ]):
                    self.pipeline._face_cache_valid = False
                    self.pipeline._last_face_detections = []
                    if hasattr(self.pipeline, "smoothing") and hasattr(
                        self.pipeline.smoothing, "active_boxes"
                    ):
                        self.pipeline.smoothing.active_boxes = [
                            b
                            for b in self.pipeline.smoothing.active_boxes
                            if b.get("class_name") != "face"
                        ]
                    with self._infer_lock:
                        self._async_state = None

        if pending_vcam is not None:
            self._apply_vcam_change(pending_vcam)
        return config

    def _inference_worker_loop(self):
        """Luồng suy luận AI chạy nền tách biệt khỏi luồng xuất hình camera (Zero-Stutter Streaming)."""
        while not self._infer_stop and self.running:
            if not self._infer_event.wait(timeout=0.05):
                continue
            self._infer_event.clear()
            if self._infer_stop or not self.running:
                break
            with self._infer_lock:
                job = self._latest_infer_job
                self._latest_infer_job = None
            if job is None:
                continue
            infer_frame, infer_classes = job
            try:
                with self._pipeline_lock:
                    dets, unsupported, infer_ms = self.pipeline.detect_and_smooth(
                        infer_frame, selected_classes=infer_classes
                    )
                with self._infer_lock:
                    self._async_state = (list(dets), list(unsupported), float(infer_ms), None)
            except Exception as exc:
                logger.error("Async inference error: %s", exc, exc_info=True)
                with self._infer_lock:
                    self._async_state = ([], [], 0.0, str(exc))

    def _apply_vcam_change(self, enabled):
        """Bật/tắt virtual camera output trong worker thread."""
        if enabled and self.virtual_output is None:
            try:
                width = self.pipeline.config.get("camera.width", 640)
                height = self.pipeline.config.get("camera.height", 480)
                fps = self.pipeline.config.get("camera.fps", 30)
                self.virtual_output = VirtualCameraOutput(width, height, fps)
                self.virtual_output.open()
                logger.info("Virtual camera opened")
            except Exception as exc:
                self.camera_error.emit(f"Không mở được virtual camera: {exc}")
                self.virtual_output = None
        elif not enabled and self.virtual_output is not None:
            try:
                self.virtual_output.close()
            except Exception:
                pass
            self.virtual_output = None
            logger.info("Virtual camera closed")

    def run(self):
        logger.info("Opening camera index %d", self.device_index)
        cap = self.capture_factory(self.device_index)
        self._capture = cap

        # Thiết lập kích thước mặc định và giảm tối đa độ trễ buffer phần cứng
        width = self.pipeline.config.get("camera.width", 640)
        height = self.pipeline.config.get("camera.height", 480)
        requested_fps = self.pipeline.config.get("camera.fps", 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, requested_fps)
        max_read_failures = self.pipeline.config.get("camera.max_read_failures", 30)
        retry_delay = (
            self.pipeline.config.get("camera.read_retry_delay_ms", 30) / 1000.0
        )

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
            logger.error("Cannot open camera index %d", self.device_index)
            self.running = False
            self.camera_error.emit(f"Không mở được camera index {self.device_index}")

        use_async = hasattr(self.pipeline, "detect_and_smooth") and hasattr(
            self.pipeline, "render_masked_frame"
        )
        infer_thread = None
        self._infer_stop = False
        self._async_state = None
        self._latest_infer_job = None
        if use_async and self.running:
            infer_thread = threading.Thread(
                target=self._inference_worker_loop,
                name="PrivacyShield-AI-Worker",
                daemon=True,
            )
            infer_thread.start()

        consecutive_read_failures = 0
        last_frame_time = time.perf_counter()

        try:
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
                    with self._pipeline_lock:
                        faces = self.pipeline.face_recognizer.detect_faces(frame)
                        if faces:
                            best_face = max(faces, key=lambda f: f["bbox"][2] * f["bbox"][3])
                            xmin, ymin, w, h = best_face["bbox"]

                            if w >= 100 and h >= 100:
                                detected_pose = self.pipeline.face_recognizer.estimate_head_pose(
                                    best_face["face_object"]
                                )
                                if detected_pose != self.enroll_pose_index:
                                    pose_names = {
                                        0: "Nhìn Thẳng",
                                        1: "Nghiêng Trái",
                                        2: "Nghiêng Phải",
                                    }
                                    detected_names = {
                                        -2: "Cúi/Ngửa đầu",
                                        0: "Nhìn Thẳng",
                                        1: "Nghiêng Trái",
                                        2: "Nghiêng Phải",
                                    }
                                    if time.time() - self.enroll_start_time > 5.0:
                                        idx = self.enroll_pose_index
                                        self.enroll_pose_index = -1
                                        self.enroll_result.emit(
                                            False,
                                            f"Đăng ký thất bại: Phát hiện tư thế {detected_names.get(detected_pose, 'Không xác định')} (Yêu cầu: {pose_names[idx]}). Hãy thực hiện đúng hướng dẫn!",
                                        )
                                else:
                                    try:
                                        success = self.pipeline.face_recognizer.register_face_pose(
                                            frame,
                                            best_face["bbox"],
                                            self.enroll_pose_index,
                                            face_object=best_face.get("face_object"),
                                        )
                                    except TypeError:
                                        success = self.pipeline.face_recognizer.register_face_pose(
                                            frame, best_face["bbox"], self.enroll_pose_index
                                        )
                                    if success:
                                        idx = self.enroll_pose_index
                                        self.enroll_pose_index = -1
                                        self.enroll_result.emit(
                                            True, f"Đã quét thành công góc mặt {idx + 1}/3!"
                                        )
                                    else:
                                        self.enroll_pose_index = -1
                                        self.enroll_result.emit(
                                            False,
                                            "Đăng ký thất bại: Lỗi trích xuất vector đặc trưng.",
                                        )
                            else:
                                if time.time() - self.enroll_start_time > 5.0:
                                    self.enroll_pose_index = -1
                                    self.enroll_result.emit(
                                        False,
                                        "Đăng ký thất bại: Hãy di chuyển khuôn mặt lại gần camera hơn!",
                                    )
                        else:
                            if time.time() - self.enroll_start_time > 4.0:
                                self.enroll_pose_index = -1
                                self.enroll_result.emit(
                                    False,
                                    "Đăng ký thất bại: Không tìm thấy khuôn mặt rõ ràng trong khung hình!",
                                )

                # 2. Xử lý qua pipeline (thread-safe config read)
                safe_mode, override_mask, classes = self._get_config()
                if safe_mode:
                    self.pipeline.masker.override_mask_mode = override_mask
                    if not use_async:
                        processed_frame, metrics = self.pipeline.process_frame(
                            frame, selected_classes=classes
                        )
                    else:
                        with self._infer_lock:
                            async_state = self._async_state

                        if async_state is None:
                            # Frame đầu tiên: chạy đồng bộ 1 lần để đảm bảo Fail-Closed ngay từ frame 0
                            try:
                                with self._pipeline_lock:
                                    dets, unsupported, infer_ms = self.pipeline.detect_and_smooth(
                                        frame, selected_classes=classes
                                    )
                                async_state = (list(dets), list(unsupported), float(infer_ms), None)
                            except Exception as exc:
                                logger.error("Initial inference error: %s", exc, exc_info=True)
                                if not getattr(self.pipeline, "fail_safe", True):
                                    raise
                                async_state = ([], [], 0.0, str(exc))
                            with self._infer_lock:
                                self._async_state = async_state
                        else:
                            # Các frame tiếp theo: đẩy frame mới nhất sang luồng AI nền (không chặn luồng video)
                            with self._infer_lock:
                                self._latest_infer_job = (frame, list(classes))
                            self._infer_event.set()

                        dets, unsupported, infer_ms, err_msg = async_state
                        if err_msg is not None:
                            if getattr(self.pipeline, "fail_safe", True):
                                processed_frame = self.pipeline.privacy_screen(
                                    frame, "PIPELINE ERROR - SAFE MODE ACTIVE"
                                )
                                metrics = {
                                    "fps": 0.0,
                                    "latency_ms": 0.0,
                                    "detected_count": 0,
                                    "detections": [],
                                    "error": err_msg,
                                    "state": "error",
                                }
                            else:
                                raise RuntimeError(err_msg)
                        else:
                            processed_frame, metrics = self.pipeline.render_masked_frame(
                                frame, dets, unsupported, infer_ms
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
        finally:
            self._infer_stop = True
            self._infer_event.set()
            if infer_thread is not None and infer_thread.is_alive():
                infer_thread.join(timeout=2.0)
            cap.release()
            self._capture = None
            if self.virtual_output is not None:
                self.virtual_output.close()
            self.pipeline.reset_tracking()
            logger.info("Capture and output resources released")

    @staticmethod
    def _blank_frame(width, height):
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
