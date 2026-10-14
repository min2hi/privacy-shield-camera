import cv2


def clip_bbox(bbox, frame_shape):
    """Normalize and clip an xyxy box to a frame, returning an empty box if invalid."""
    h, w = frame_shape[:2]
    x1, y1, x2, y2 = (int(value) for value in bbox)
    # Fix: đảm bảo thứ tự tọa độ đúng trước khi clip
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    x1 = min(max(0, x1), w)
    x2 = min(max(0, x2), w)
    y1 = min(max(0, y1), h)
    y2 = min(max(0, y2), h)
    return x1, y1, x2, y2

def expand_bbox(bbox, frame_shape, ratio=0.15):
    """
    Mở rộng bounding box theo tỷ lệ phần trăm (giữ nguyên tâm).
    bbox: (x1, y1, x2, y2)
    frame_shape: (height, width)
    ratio: Tỷ lệ mở rộng (ví dụ 0.15 = 15%)
    """
    h, w = frame_shape[:2]
    x1, y1, x2, y2 = clip_bbox(bbox, frame_shape)

    bw = x2 - x1
    bh = y2 - y1

    dw = int(bw * ratio)
    dh = int(bh * ratio)

    # Mở rộng ra các hướng nhưng không vượt quá biên frame
    nx1 = max(0, x1 - dw)
    ny1 = max(0, y1 - dh)
    nx2 = min(w, x2 + dw)
    ny2 = min(h, y2 + dh)

    return nx1, ny1, nx2, ny2


def apply_solid_mask(frame, bbox, color=(0, 0, 0)):
    """
    Che hoàn toàn vùng bbox bằng hình chữ nhật màu đơn sắc (mặc định là đen).
    """
    x1, y1, x2, y2 = clip_bbox(bbox, frame.shape)
    if x2 <= x1 or y2 <= y1:
        return
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)


def apply_gaussian_blur(frame, bbox, kernel_size=51):
    """
    Làm mờ vùng bbox bằng bộ lọc Gauss (Gaussian Blur).
    """
    x1, y1, x2, y2 = clip_bbox(bbox, frame.shape)
    if x2 <= x1 or y2 <= y1:
        return

    roi = frame[y1:y2, x1:x2]
    max_kernel = max(1, min(roi.shape[0], roi.shape[1]))
    if max_kernel % 2 == 0:
        max_kernel -= 1
    effective_kernel = min(kernel_size, max_kernel)
    if effective_kernel % 2 == 0:
        effective_kernel -= 1
    effective_kernel = max(1, effective_kernel)
    blurred = cv2.GaussianBlur(roi, (effective_kernel, effective_kernel), 0)
    frame[y1:y2, x1:x2] = blurred


def apply_mosaic(frame, bbox, block_size=None):
    """
    Tạo hiệu ứng điểm ảnh ô vuông (Mosaic) trên vùng bbox.
    """
    x1, y1, x2, y2 = clip_bbox(bbox, frame.shape)
    if x2 <= x1 or y2 <= y1:
        return

    roi = frame[y1:y2, x1:x2]
    roi_h, roi_w = roi.shape[:2]

    # Scale block_size tự động theo kích thước ROI nếu không được chỉ định
    if block_size is None:
        block_size = max(12, int(min(roi_w, roi_h) * 0.15))
    # Tránh lỗi chia cho 0 nếu roi quá nhỏ
    block_w = max(1, roi_w // block_size)
    block_h = max(1, roi_h // block_size)

    # Thu nhỏ xuống rồi phóng to lại để tạo ô vuông pixel
    small = cv2.resize(roi, (block_w, block_h), interpolation=cv2.INTER_LINEAR)
    mosaic = cv2.resize(small, (roi_w, roi_h), interpolation=cv2.INTER_NEAREST)
    frame[y1:y2, x1:x2] = mosaic


class Masker:
    def __init__(self, class_mask_presets=None, default_mask_mode="mosaic", expand_ratio=0.15):
        """
        class_mask_presets: Map tên class với cách che (Risk Level).
        default_mask_mode: Cách che mặc định nếu class không nằm trong preset.
        expand_ratio: Tỷ lệ mở rộng bbox.
        """
        self.class_mask_presets = class_mask_presets or {}
        self.default_mask_mode = default_mask_mode
        self.expand_ratio = expand_ratio
        self.override_mask_mode = None

    def apply_masks(self, frame, detections):
        """
        Đọc các bbox và áp dụng mặt nạ che tương ứng lên frame.
        """
        processed_frame = frame.copy()
        h, w = processed_frame.shape[:2]

        for det in detections:
            class_name = det["class_name"]
            bbox = det["bbox"]

            # 1. Mở rộng bounding box
            expanded_box = expand_bbox(bbox, (h, w), self.expand_ratio)

            # 2. Xác định phương pháp che (Ưu tiên: Override động từ GUI > Custom mask_mode trong bbox > Presets của Class)
            mask_mode = (
                self.override_mask_mode
                if self.override_mask_mode
                else (det.get("mask_mode") or self.class_mask_presets.get(class_name, self.default_mask_mode))
            )

            # 3. Áp dụng hiệu ứng
            if mask_mode == "solid_mask":
                apply_solid_mask(processed_frame, expanded_box)
            elif mask_mode == "gaussian_blur":
                apply_gaussian_blur(processed_frame, expanded_box)
            elif mask_mode == "mosaic":
                apply_mosaic(processed_frame, expanded_box)
            else:
                # Fallback mặc định
                apply_mosaic(processed_frame, expanded_box)

        return processed_frame
