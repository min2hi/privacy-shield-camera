# ĐẶC TẢ KIẾN TRÚC HỆ THỐNG & HẠ TẦNG CHI TIẾT (V3 - BỔ SUNG TỐI ƯU HÓA & PRIVACY POLICY)

Tài liệu này được biên soạn bởi **Senior Developer/Architect** nhằm đặc tả chi tiết toàn bộ kiến trúc hệ thống **Real-Time Privacy Shield Camera**, tích hợp các cơ chế tối ưu hóa hiệu năng, phân cấp rủi ro bảo mật và bộ quy tắc kiểm thử sản phẩm dùng cho đồ án.

---

## 1. Bức Tranh Toàn Cảnh (3-Layer Architecture)

Dự án được chia thành 3 phân lớp độc lập để giải quyết bài toán: **Hiệu năng thực tế thời gian thực (Real-time)** và **Tính thông minh khi hỗ trợ phát triển (Agentic Helper)**.

```
                     ┌──────────────────────────────────┐
                     │       DỰ ÁN PRIVACY SHIELD       │
                     └────────────────┬─────────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         ▼                            ▼                            ▼
┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│  LỚP A: DESKTOP  │         │   LỚP B: MODEL   │         │ LỚP C: PROJECT   │
│  APP (SẢN PHẨM)  │         │     PIPELINE     │         │  AGENT (TRỢ LÝ)  │
├──────────────────┤         ├──────────────────┤         ├──────────────────┤
│ - Đọc webcam     │         │ - Tạo dataset giả│         │ - RAG tài liệu   │
│ - Chạy YOLOv8    │         │ - Label bounding │         │ - Quản lý code   │
│ - OpenCV Masking │         │ - Train custom   │         │ - Ghi nhớ design │
│ - Virtual Camera │         │ - Đánh giá mAP   │         │ - Log & Trace    │
└──────────────────┘         └──────────────────┘         └──────────────────┘
```

---

## 2. Chi Tiết Stack Kỹ Thuật & Lý Do Lựa Chọn (Why This Stack?)

### 2.1. Lớp A: Privacy Shield Desktop App (Sản phẩm chính)

| Công nghệ | Vai trò trong hệ thống | **Lý do lựa chọn (Senior Dev Rationale)** |
| :--- | :--- | :--- |
| **Python** | Ngôn ngữ phát triển chính | Hệ sinh thái AI/ML mạnh nhất. Cho phép viết code nhanh và có các thư viện wrapper tối ưu bằng C++ ở dưới (như OpenCV, PyTorch). |
| **OpenCV** | Đọc/ghi video, xử lý ảnh | Bộ thư viện thị giác máy tính chuẩn công nghiệp. Thao tác xử lý ma trận ảnh (Numpy array) cực kỳ nhanh, giúp thực hiện các phép Blur, Mosaic, Solid Mask chỉ mất dưới **1-2ms**. |
| **YOLOv8** | Nhận diện vật thể nhạy cảm | *Lý do vượt trội*: Tốc độ suy luận (Inference) cực nhanh. Bản YOLOv8n (Nano) có thể chạy ở mức **15-25ms/frame** trên CPU laptop thường, đảm bảo tổng luồng đạt trên **30 FPS** mà không cần card đồ họa rời (GPU). |
| **PySide6** | Xây dựng giao diện Desktop | Phiên bản Qt6 chính thức cho Python. Khác với Tkinter (quá đơn giản/xấu) hay Electron (nặng, tốn RAM), PySide6 cho phép vẽ khung hình OpenCV thời gian thực rất mượt mà nhờ việc ánh xạ trực tiếp Numpy Array -> QImage mà không gây nghẽn RAM. |
| **pyvirtualcam** | Xuất luồng ra OBS/Zoom | Kết nối trực tiếp với driver webcam ảo của hệ điều hành. Giúp chuyển đổi luồng frame đã che mờ thành một đầu vào camera tiêu chuẩn để mọi ứng dụng họp trực tuyến nhận diện được. |

### 2.2. Lớp C: AI Project Agent (Hạ tầng hỗ trợ)

| Công nghệ | Vai trò trong hạ tầng | **Lý do lựa chọn (Senior Dev Rationale)** |
| :--- | :--- | :--- |
| **LangGraph** | Điều phối Agent | Hỗ trợ luồng chạy dạng Đồ thị (State Graph) có vòng lặp. Khác với LangChain (chạy thẳng), LangGraph cho phép Agent: Lập kế hoạch -> Chạy test -> Phát hiện lỗi -> Tự sửa đổi code cho đến khi đúng (Self-reflection). |
| **PostgreSQL + pgvector** | Bộ nhớ dài hạn & RAG | Cho phép lưu trữ dữ liệu quan hệ (lịch sử quyết định kỹ thuật của dự án) và dữ liệu vector nhúng (tài liệu RAG) trong cùng một cơ sở dữ liệu. Chạy hoàn toàn offline qua Docker, bảo mật tuyệt đối. |
| **Redis** | Bộ nhớ ngắn hạn | Lưu giữ trạng thái (checkpoint) của cuộc hội thoại hiện tại. Giúp khôi phục lại trạng thái làm việc của Agent ngay lập tức nếu tiến trình bị khởi động lại. |
| **Langfuse** | Giám sát & Tracing (AgentOps) | Thay thế mã nguồn mở hoàn hảo cho LangSmith. Cho phép cài đặt local thông qua Docker, ghi nhận chi tiết từng node LLM chạy, đo latency và chi phí token mà không sợ dữ liệu bị đẩy lên server của bên thứ ba. |
| **LiteLLM** | Quản lý cổng kết nối LLM | Đóng vai trò là Gateway. Bạn chỉ cần viết code gọi API theo chuẩn OpenAI, LiteLLM sẽ tự động định tuyến đến OpenAI GPT-4, Google Gemini, hoặc Ollama (chạy model local hoàn toàn miễn phí) mà không cần đổi một dòng code nào trong Agent. |

---

## 3. Tối Ưu Hệu Năng Thực Tế: Frame Skipping & Bbox Reuse

Để ứng dụng có thể chạy mượt mà ở tốc độ 30 FPS trên các máy tính thông thường (ví dụ: Core i5, 12GB RAM không có GPU rời), hệ thống áp dụng cơ chế **Frame Skipping & Bbox Reuse**:

* **Nguyên lý hoạt động**:
  * **Frame $t$ (Chạy YOLO)**: Nhận raw frame -> Gọi mô hình YOLOv8 để phát hiện vật thể -> Lấy Bounding Box (Bbox) -> Áp dụng Masking và lưu lại Bbox vào bộ đệm (Buffer).
  * **Frame $t+1$ (Bỏ qua YOLO)**: Nhận raw frame -> Bỏ qua suy luận YOLO -> Tái sử dụng (Reuse) trực tiếp Bbox từ bộ đệm của Frame $t$ -> Áp dụng Masking và xuất kết quả.
* **Lợi ích**: Giảm một nửa số lần gọi GPU/CPU để suy luận mô hình (Inference), giúp giảm nhiệt độ máy, tiết kiệm RAM và duy trì FPS cực kỳ ổn định.
* **Hỗ trợ kết hợp**: Nhờ module `temporal_smoothing.py` và `bbox_expansion.py`, việc tái sử dụng Bbox ở frame xen kẽ hoàn toàn không gây ra hiện tượng lệch vùng che hay nhấp nháy ngay cả khi vật thể chuyển động.

---

## 4. Phân Cấp Mức Độ Rủi Ro Bảo Mật (Privacy Risk Levels)

Không phải mọi vật thể nhạy cảm đều có tính riêng tư như nhau. Hệ thống tự động phân loại mức rủi ro để đưa ra bộ lọc che mờ mặc định phù hợp nhất:

| Vật thể (Object) | Mức rủi ro | Bộ lọc mặc định (Default Masking) | Lý do |
| :--- | :--- | :--- | :--- |
| **id_card_fake** (Căn cước công dân) | **Rất cao (Critical)** | **Solid Mask** (Khối màu đè lên) | Chứa số định danh cá nhân, khuôn mặt, ngày sinh. Gaussian Blur có thể bị các thuật toán khử mờ dịch lại thông tin. |
| **credit_card_fake** (Thẻ ngân hàng) | **Rất cao (Critical)** | **Solid Mask** | Chứa số thẻ, ngày hết hạn và tên chủ thẻ. Cần che tuyệt đối bằng khối màu đè. |
| **qr_code** (Mã QR) | **Cao (High)** | **Solid Mask hoặc Mosaic mạnh** | Các camera hiện đại có thể quét được mã QR từ khoảng cách xa ngay cả khi bị mờ nhẹ. |
| **receipt** (Hóa đơn mua sắm) | **Trung bình-cao (Medium-High)** | **Mosaic** (Pixelation) | Chứa địa chỉ nhà, số điện thoại, lịch sử mua sắm cá nhân. |
| **smartphone_screen** (Màn hình điện thoại) | **Trung bình-cao (Medium-High)** | **Mosaic hoặc Blur mạnh** | Chứa tin nhắn riêng tư, ứng dụng tài chính. |
| **document** (Tài liệu văn bản giấy) | **Trung bình (Medium)** | **Gaussian Blur** | Chứa nội dung văn bản thông thường. |

---

## 5. Chính Sách Không Lưu Dữ Liệu Thô (No Raw Frame Policy)

Để chứng minh ứng dụng thực sự đặt quyền riêng tư của người dùng lên hàng đầu, hệ thống tuân thủ nghiêm ngặt **Chính sách không lưu dữ liệu thô (No Raw Frame Policy)**:

```text
- KHÔNG lưu trữ bất kỳ raw frame (khung hình thô) nào từ webcam vào đĩa cứng (disk).
- KHÔNG ghi hình hoặc lưu video gốc chưa xử lý.
- KHÔNG gửi/upload frame video hoặc ảnh gốc lên bất kỳ cloud server nào.
- KHÔNG đưa hình ảnh webcam thô vào đầu vào của AI Agent/LLM Copilot.
- Khi xảy ra lỗi hệ thống (Pipeline Exception), ngắt hoàn toàn kết nối Virtual Cam hoặc phát Privacy Screen (Màn hình đen/tím thông báo lỗi) để bảo vệ, tuyệt đối không xuất hình thô chưa che.
```

### Thiết kế Log Hợp Lệ (Chỉ log metadata):
Hệ thống chỉ ghi nhật ký (log) thông tin thống kê hiệu năng dưới dạng cấu trúc JSON sạch, không chứa thông tin pixel:
```json
{
  "timestamp": "2026-06-27T00:45:00Z",
  "fps": 29.4,
  "latency_ms": 18.2,
  "detected_objects": [
    {
      "class": "id_card_fake",
      "confidence": 0.88,
      "mask_mode": "solid_mask",
      "bbox_area_ratio": 0.08
    }
  ]
}
```

---

## 6. Luồng Đi Của Dữ Liệu Tối Ưu (Data Flow)

```text
[Webcam Input]
       │
       ▼
[Frame Scheduler] ──> (Bỏ qua frame? Có) ──> [Tái sử dụng Bbox từ Buffer] ──┐
       │                                                                  │
  (Không chạy YOLO)                                                       │
       │                                                                  │
 (Chạy YOLO - Không)                                                      │
       ▼                                                                  │
[Detector (YOLOv8)] ──> [Lấy Bbox mới & lưu Buffer]                       │
       │                                                                  │
       ├──────────────────────────────────────────────────────────────────┘
       ▼
[Temporal Smoothing] (Chống nhấp nháy vùng che)
       │
       ▼
[Bbox Expansion] (Mở rộng vùng che thêm 15%)
       │
       ▼
[Masking Filter] (Áp dụng bộ lọc tùy theo Risk Level của vật thể)
       │
       ▼
┌──────┴─────────────────────────┐
▼                                ▼
[UI Preview (PySide6)]   [Virtual Camera Output] ──> [OBS/Zoom]
```

---

## 7. Kịch Bản Demo Bảo Vệ Đồ Án (Demo Script)

Kịch bản demo được thiết kế thành 5 bước trực quan giúp thuyết phục hội đồng giám khảo:

* **Demo 1: Smoke Test với Camera**
  * *Hành động*: Bật app, chọn nguồn webcam, đưa điện thoại (smartphone) trước camera.
  * *Kết quả*: Khung hình hiển thị mượt mà, màn hình điện thoại lập tức bị che mờ bằng bộ lọc Mosaic mặc định.
* **Demo 2: Che mờ thông tin chuyên biệt (Thẻ giả/Hóa đơn giả)**
  * *Hành động*: Đưa thẻ căn cước công dân giả (hoặc thẻ ngân hàng giả) đã in sẵn trước camera.
  * *Kết quả*: Hệ thống nhận diện đúng nhãn `id_card_fake` / `credit_card_fake` và lập tức đè một khối màu Solid Mask lên (không dùng blur để đảm bảo an toàn).
* **Demo 3: Thử nghiệm các chế độ che và thay đổi Slider**
  * *Hành động*: Thay đổi chế độ từ Solid Mask -> Mosaic -> Gaussian Blur trên giao diện điều khiển. Kéo thanh slider Confidence để thay đổi độ nhạy nhận diện.
  * *Kết quả*: Vùng che thay đổi kiểu hiển thị trực quan ngay lập tức.
* **Demo 4: Thử nghiệm tính năng Fail-safe**
  * *Hành động*: Nhấn nút giả lập lỗi hệ thống (Simulate Pipeline Error).
  * *Kết quả*: Luồng video trên OBS/Zoom lập tức chuyển sang màn hình bảo vệ (Privacy Screen) màu tím đen kèm dòng chữ "Privacy Shield Failsafe Active", hoàn toàn không bị rò rỉ frame thô.
* **Demo 5: Kết nối trực tiếp OBS/Zoom**
  * *Hành động*: Mở phần mềm OBS Studio, add nguồn video đầu vào là "Privacy Shield Virtual Camera".
  * *Kết quả*: Streamer di chuyển thẻ trước webcam vật lý, luồng stream trên OBS hiển thị hình ảnh đã được che mờ hoàn hảo.

---

## 8. Bộ Checklist Kiểm Thử Toàn Diện (Testing Checklist)

Để đảm bảo chất lượng hệ thống đạt điểm A+, chúng ta cần hoàn thành các bài test sau:

### 8.1. Functional Tests (Kiểm thử chức năng)
- [ ] Khởi động và kết nối thành công với các nguồn Webcam vật lý khác nhau.
- [ ] Bật/tắt chế độ bảo mật (Privacy Mode) trực tiếp từ giao diện.
- [ ] Thay đổi các chế độ lọc (Blur, Mosaic, Solid) hoạt động đúng logic.
- [ ] Slider thay đổi ngưỡng tin cậy (Confidence threshold) hoạt động trực tiếp.
- [ ] OBS/Zoom nhận dạng được luồng Virtual Camera.

### 8.2. Privacy Tests (Kiểm thử an toàn thông tin)
- [ ] Vật thể rủi ro cao (ID Card, Credit Card) bắt buộc phải dùng Solid Mask làm mặc định.
- [ ] Khi xảy ra crash/exception, hệ thống lập tức khóa cổng Virtual Cam (không xuất frame thô).
- [ ] Kiểm tra ổ cứng xem có file ảnh thô hoặc video thô nào tự động lưu hay không (kết quả phải là Không).
- [ ] Log hệ thống tuyệt đối không chứa dữ liệu nhạy cảm dạng ảnh hay text chưa mã hóa.

### 8.3. Performance Tests (Kiểm thử hiệu năng)
- [ ] FPS trung bình duy trì ổn định trên **25 FPS** khi chạy ở độ phân giải 720p.
- [ ] CPU/RAM usage không tăng đột biến (memory leak) khi chạy liên tục trong 30 phút.
- [ ] Đo đạc và so sánh độ trễ (Latency ms) khi bật và tắt chế độ **Frame Skipping**.

### 8.4. Robustness Tests (Kiểm thử độ bền bỉ)
- [ ] Kiểm tra nhận diện dưới ánh sáng yếu (đèn ngủ) và ánh sáng cực mạnh (đèn học rọi trực tiếp).
- [ ] Kiểm tra nhận diện khi vật thể nghiêng góc 30° hoặc 45° so với camera.
- [ ] Kiểm tra tính năng **Temporal Smoothing** bằng cách di chuyển thẻ nhanh trước camera (vùng che không được phép biến mất/chớp tắt).

---

## 9. Đạo Đức Dữ Liệu & Dữ Liệu Giả Lập (Dataset Ethics)

Một phần quan trọng của báo cáo đồ án là chứng minh tính hợp pháp và đạo đức của dữ liệu:
* Dự án cam kết **không sử dụng thông tin cá nhân thật** (thẻ CCCD thật, thẻ tín dụng thật) của bất kỳ ai trong quá trình thu thập dataset và huấn luyện mô hình.
* Toàn bộ dữ liệu huấn luyện cho lớp `id_card_fake` và `credit_card_fake` được tự thiết kế (sử dụng các công cụ vẽ mẫu thẻ giả với tên người và số ngẫu nhiên) và in ra giấy cứng để chụp ảnh/quay video làm mẫu.
* Điều này giúp ứng dụng tuân thủ hoàn toàn luật an toàn thông tin (GDPR / Luật an toàn thông tin mạng Việt Nam) và ghi điểm tuyệt đối về mặt đạo đức nghiên cứu trước hội đồng giám khảo.

---

## 10. Phân Định Phạm Vi Phát Triển (MVP vs. A+ Tier)

Để tránh tình trạng quá tải và mất tập trung trong giai đoạn đầu, dự án phân cấp mục tiêu rõ ràng:

### 10.1. Mức MVP (Tối thiểu phải chạy được để đạt yêu cầu)
1. Đọc webcam ổn định bằng OpenCV.
2. Load model YOLOv8n pretrained để chạy smoke test với class `cell phone`.
3. Cắt tọa độ bounding box, áp dụng Gaussian Blur lên vùng đó.
4. Hiển thị khung preview trên màn hình OpenCV đơn giản.
5. Đo đạc và hiển thị số FPS cơ bản.

### 10.2. Mức Đồ Án Hoàn Chỉnh (Đủ điểm giỏi)
1. Có tập dữ liệu custom cho 4 class nhạy cảm chính: `id_card_fake`, `credit_card_fake`, `receipt`, `smartphone_screen`.
2. Huấn luyện thành công model YOLOv8n trên dataset này.
3. Hỗ trợ đầy đủ 3 chế độ che: Blur, Mosaic, Solid Mask.
4. Có cơ chế **Temporal Smoothing** chống chớp tắt và **Bbox Expansion** mở rộng vùng che.
5. Có giao diện đồ họa GUI viết bằng PySide6 hiện đại.
6. Hoàn thiện báo cáo đánh giá model (Precision, Recall, mAP, FPS).

### 10.3. Mức Điểm A+ (Tối ưu hóa và Đột phá)
1. Kết nối thành công Virtual Camera hiển thị tốt trên OBS/Zoom.
2. Áp dụng cơ chế tối ưu **Frame Skipping + Reuse Bbox** để giảm tải CPU.
3. Tích hợp cơ chế **Fail-safe** tự động hiển thị Privacy Screen khi hệ thống gặp lỗi.
4. Train và so sánh chất lượng/hiệu năng giữa hai phiên bản YOLOv8n và YOLOv8s.
5. Triển khai AI Project Agent trong Docker (LangGraph, PostgreSQL, Redis, Langfuse) để quản lý tài liệu và hỗ trợ lập trình viên.

---

## 11. Thứ Tự Triển Khai Thực Tế (Roadmap sửa đổi)

```
[Pha 0: Setup môi trường]
       │
       ▼
[Pha 1: Core pipeline không GUI (OpenCV + YOLO pretrained)]
       │
       ▼
[Pha 2: Tối ưu Realtime (Frame skipping + Temporal smoothing)]
       │
       ▼
[Pha 3: Thiết kế GUI PySide6]
       │
       ▼
[Pha 4: Huấn luyện Custom Model (Dataset giả -> Train -> Integration)]
       │
       ▼
[Pha 5: Tích hợp Virtual Camera cho OBS/Zoom]
       │
       ▼
[Pha 6: Setup AI Project Agent hỗ trợ quản lý dự án]
```

---

*Tài liệu này là kim chỉ nam kiến trúc cho toàn bộ dự án. Hãy báo cho tôi biết nếu bạn đã sẵn sàng để chúng ta bắt đầu coding Pha 0 và Pha 1.*
