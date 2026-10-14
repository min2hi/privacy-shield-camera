class FrameScheduler:
    def __init__(self, enabled=True, skip_ratio=2):
        """
        enabled: Có bật chế độ Frame Skipping hay không.
        skip_ratio: Tỷ lệ skip. Ví dụ skip_ratio = 2 nghĩa là cứ 2 frame thì chạy YOLO 1 lần (ở frame đầu tiên),
                    frame tiếp theo sẽ dùng lại bbox cũ.
        """
        self.enabled = enabled
        self.skip_ratio = max(1, skip_ratio)
        self.frame_counter = 0
        self.last_detections = []

    def should_detect(self):
        """
        Quyết định xem frame hiện tại có cần chạy YOLO để detect hay không.
        """
        if not self.enabled:
            return True
        
        # Chạy detect khi bộ đếm chia hết cho skip_ratio
        return (self.frame_counter % self.skip_ratio) == 0

    def update_detections(self, detections):
        """
        Cập nhật danh sách bbox mới nhất từ YOLO và tăng bộ đếm frame.
        """
        self.last_detections = detections
        self.frame_counter = (self.frame_counter + 1) % self.skip_ratio

    def get_last_detections(self):
        """
        Lấy bản sao danh sách bbox của lần detect gần nhất.
        """
        return list(self.last_detections)

    def skip_frame(self):
        """
        Tăng bộ đếm frame khi bỏ qua việc chạy YOLO (reuse bbox).
        """
        self.frame_counter = (self.frame_counter + 1) % self.skip_ratio

    def reset(self):
        """Drop cached detections when a capture/model/policy session changes."""
        self.frame_counter = 0
        self.last_detections = []
