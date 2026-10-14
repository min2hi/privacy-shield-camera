# 02 — Problem Definition

Input là BGR webcam frame. Output là frame cùng kích thước đã che mọi detection thuộc policy đang bật, hoặc privacy screen nếu pipeline/output không đáng tin cậy.

Trạng thái lớp phải thuộc một trong ba nhóm: `supported` (model bundle có class), `disabled` (người dùng chủ động bỏ chọn nhưng UI cảnh báo), hoặc `unsupported` (config yêu cầu nhưng model không có class). Không được coi `unsupported` là “không phát hiện thấy”.

Các target dự kiến: phone/screen, QR, receipt, document, synthetic ID card và synthetic payment card. Face masking là pipeline riêng với threat model sinh trắc học.

Ưu tiên chất lượng: giảm false negative cho lớp critical, đồng thời báo coverage/false positive/latency thay vì chỉ một accuracy tổng.
