# 19 — Risks and Limitations

- Detector có thể miss vật nhỏ, mờ, nghiêng, phản sáng hoặc bị che khuất.
- Temporal hold giảm chớp nhưng có thể che vùng cũ khi vật di chuyển nhanh.
- Blur/mosaic không phù hợp cho dữ liệu critical; solid mask là default an toàn hơn.
- COCO model hiện không hỗ trợ phần lớn privacy classes trong config.
- Face recognition có bias/false match; embedding là biometric data nhạy cảm.
- Virtual-camera backend phụ thuộc driver và ứng dụng nhận.
- CPU/FPS thay đổi theo máy, camera và số mặt; chưa có benchmark release.
- Synthetic data có domain gap; metrics không đại diện mọi giấy tờ/ngôn ngữ/quốc gia.
- Agent infrastructure tăng attack surface và không cần thiết cho desktop runtime.

Sản phẩm không thay thế kiểm soát chia sẻ màn hình, DLP, redaction thủ công hay tư vấn pháp lý. Không tuyên bố GDPR/luật Việt Nam “hoàn toàn compliant” chỉ dựa trên thiết kế.
