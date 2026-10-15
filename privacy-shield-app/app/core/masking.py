from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import cv2
import numpy as np


def clip_bbox(
    bbox: Sequence[float | int], frame_shape: Sequence[int] | tuple[int, ...]
) -> tuple[int, int, int, int]:
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

def expand_bbox(
    bbox: Sequence[float | int], frame_shape: Sequence[int] | tuple[int, ...], ratio: float = 0.15
) -> tuple[int, int, int, int]:
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


def apply_solid_mask(
    frame: np.ndarray, bbox: Sequence[float | int], color: tuple[int, int, int] = (0, 0, 0)
) -> None:
    """
    Che hoàn toàn vùng bbox bằng hình chữ nhật màu đơn sắc (mặc định là đen).
    """
    x1, y1, x2, y2 = clip_bbox(bbox, frame.shape)
    if x2 <= x1 or y2 <= y1:
        return
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)


def apply_gaussian_blur(
    frame: np.ndarray, bbox: Sequence[float | int], kernel_size: int = 51
) -> None:
    """
    Làm mờ vùng bbox bằng bộ lọc Gauss (Gaussian Blur).
    Tối ưu hiệu năng: với vùng ROI lớn (>= 48px), thu nhỏ 4x -> làm mờ -> phóng to lại,
    giảm thời gian CPU từ ~3-10ms xuống ~0.2ms mà độ mờ vẫn mịn tương đương.
    """
    x1, y1, x2, y2 = clip_bbox(bbox, frame.shape)
    if x2 <= x1 or y2 <= y1:
        return

    roi = frame[y1:y2, x1:x2]
    roi_h, roi_w = roi.shape[:2]

    if min(roi_h, roi_w) >= 48 and kernel_size >= 21:
        small_w = max(1, roi_w // 4)
        small_h = max(1, roi_h // 4)
        small_roi = cv2.resize(roi, (small_w, small_h), interpolation=cv2.INTER_LINEAR)
        k = max(3, (kernel_size // 4) | 1)
        max_k = max(1, min(small_h, small_w))
        if max_k % 2 == 0:
            max_k -= 1
        k = max(1, min(k, max_k))
        blurred_small = cv2.GaussianBlur(small_roi, (k, k), 0)
        frame[y1:y2, x1:x2] = cv2.resize(
            blurred_small, (roi_w, roi_h), interpolation=cv2.INTER_LINEAR
        )
        return

    max_kernel = max(1, min(roi_h, roi_w))
    if max_kernel % 2 == 0:
        max_kernel -= 1
    effective_kernel = min(kernel_size, max_kernel)
    if effective_kernel % 2 == 0:
        effective_kernel -= 1
    effective_kernel = max(1, effective_kernel)
    blurred = cv2.GaussianBlur(roi, (effective_kernel, effective_kernel), 0)
    frame[y1:y2, x1:x2] = blurred


def apply_mosaic(
    frame: np.ndarray, bbox: Sequence[float | int], block_size: int | None = None
) -> None:
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
    class_mask_presets: dict[str, str]
    default_mask_mode: str
    expand_ratio: float
    override_mask_mode: str | None

    def __init__(
        self,
        class_mask_presets: dict[str, str] | None = None,
        default_mask_mode: str = "mosaic",
        expand_ratio: float = 0.15,
    ) -> None:
        """
        class_mask_presets: Map tên class với cách che (Risk Level).
        default_mask_mode: Cách che mặc định nếu class không nằm trong preset.
        expand_ratio: Tỷ lệ mở rộng bbox.
        """
        self.class_mask_presets = class_mask_presets or {}
        self.default_mask_mode = default_mask_mode
        self.expand_ratio = expand_ratio
        self.override_mask_mode = None

    def apply_masks(self, frame: np.ndarray, detections: Sequence[dict[str, Any]]) -> np.ndarray:
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

            # 2. Xác định phương pháp che
            # Face detections luôn giữ mask_mode riêng (gaussian_blur cho owner, mosaic cho stranger)
            # Override chỉ áp dụng cho object detections (card, phone, etc.)
            if det.get("class_name") == "face" and det.get("mask_mode"):
                mask_mode = det["mask_mode"]
            elif self.override_mask_mode:
                mask_mode = self.override_mask_mode
            else:
                mask_mode = det.get("mask_mode") or self.class_mask_presets.get(class_name, self.default_mask_mode)

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
