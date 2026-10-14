from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def calculate_iou(box1: Sequence[float | int], box2: Sequence[float | int]) -> float:
    """
    Tính toán chỉ số Intersection over Union (IoU) giữa 2 bounding box.
    Định dạng box: (x1, y1, x2, y2)
    """
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2

    # Tìm tọa độ vùng giao nhau
    xi1 = max(x1_1, x1_2)
    yi1 = max(y1_1, y1_2)
    xi2 = min(x2_1, x2_2)
    yi2 = min(y2_1, y2_2)

    inter_width = max(0, xi2 - xi1)
    inter_height = max(0, yi2 - yi1)
    inter_area = inter_width * inter_height

    # Tính diện tích từng box
    box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
    box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)

    union_area = box1_area + box2_area - inter_area
    if union_area == 0:
        return 0.0

    return inter_area / union_area


class TemporalSmoothing:
    hold_frames: int
    iou_threshold: float
    active_boxes: list[dict[str, Any]]

    def __init__(self, hold_frames: int = 5, iou_threshold: float = 0.3) -> None:
        """
        hold_frames: Số lượng frame giữ lại mask khi bị mất dấu (TTL).
        iou_threshold: Ngưỡng IoU tối thiểu để coi 2 bbox ở 2 frame liên tiếp là cùng 1 vật thể.
        """
        self.hold_frames = hold_frames
        self.iou_threshold = iou_threshold
        # Mỗi active_box là một dict: { 'class_name': ..., 'bbox': (x1, y1, x2, y2), 'ttl': ..., 'confidence': ... }
        self.active_boxes = []

    def reset(self) -> None:
        """Drop all tracks at session boundaries."""
        self.active_boxes = []

    def update(self, new_detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        new_detections: Danh sách bbox phát hiện mới từ detector ở frame hiện tại:
                        [{'class_name': ..., 'bbox': (x1, y1, x2, y2), 'confidence': ...}]
        Trả về: Danh sách bbox sau khi đã được làm mịn (bao gồm cả các bbox đang được giữ lại do bị miss).
        """
        # 1. Giảm TTL của tất cả các box hiện có
        for box in self.active_boxes:
            box["ttl"] -= 1

        matched_new_indices: set[int] = set()

        # 2. So khớp các phát hiện mới với các box đang theo dõi
        for active_box in self.active_boxes:
            best_iou = 0.0
            best_idx = -1

            for i, new_det in enumerate(new_detections):
                if i in matched_new_indices:
                    continue
                # Chỉ so khớp nếu cùng class
                if new_det["class_name"] != active_box["class_name"]:
                    continue

                iou = calculate_iou(active_box["bbox"], new_det["bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_idx = i

            # Nếu tìm thấy so khớp tốt hơn ngưỡng
            if best_iou >= self.iou_threshold and best_idx != -1:
                active_box["bbox"] = new_detections[best_idx]["bbox"]
                active_box["confidence"] = new_detections[best_idx]["confidence"]
                active_box["ttl"] = self.hold_frames  # Reset TTL
                active_box["mask_mode"] = new_detections[best_idx].get("mask_mode")  # Cập nhật mask_mode
                matched_new_indices.add(best_idx)

        # 3. Loại bỏ các box hết hạn (ttl <= 0)
        self.active_boxes = [box for box in self.active_boxes if box["ttl"] > 0]

        # 4. Thêm các phát hiện mới chưa được khớp vào danh sách theo dõi
        for i, new_det in enumerate(new_detections):
            if i not in matched_new_indices:
                self.active_boxes.append({
                    "class_name": new_det["class_name"],
                    "bbox": new_det["bbox"],
                    "confidence": new_det["confidence"],
                    "ttl": self.hold_frames,
                    "mask_mode": new_det.get("mask_mode")  # Lưu trữ mask_mode của bbox
                })

        # 5. Trả về danh sách bbox làm mịn
        return [
            {
                "class_name": box["class_name"],
                "bbox": box["bbox"],
                "confidence": box["confidence"],
                "mask_mode": box.get("mask_mode")  # Giữ trường mask_mode đầu ra
            }
            for box in self.active_boxes
        ]
