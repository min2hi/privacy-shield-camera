# 07 — Face Privacy

Face detection và identity verification là hai bước khác nhau. Unknown không đồng nghĩa stranger đáng tin cậy khi chưa enrollment hoặc chất lượng crop thấp.

Enrollment cần consent rõ, ba pose có quality gate và atomic save. Template là embedding chứ không phải ảnh, nhưng vẫn là dữ liệu sinh trắc nhạy cảm. Release phải có nút reset/delete, file permission phù hợp, schema/version metadata và không tự upload/ingest.

Threshold phải được đánh giá trên validation identities; giá trị hard-coded hiện tại chỉ là development default. Log không in khoảng cách từng frame trong production.
