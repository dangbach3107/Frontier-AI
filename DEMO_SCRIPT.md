# Datapot AI Learning Showcase — Demo Script

## 1. Mở đầu
"Em không muốn bắt học viên tự tạo content. Em muốn lấy trải nghiệm và sản phẩm họ đã có, sau đó AI biến nó thành nhiều format content."

## 2. Điểm khác biệt
"Nhưng em cũng không cho raw learner data đi thẳng vào LLM. Trước model có một privacy pre-processing layer."

## 3. Chạy demo
- Bấm Run Prototype.
- So sánh RAW INPUT và SANITIZED INPUT.
- Chỉ ra [EMAIL], [CUSTOMER_INFO], [BUSINESS_METRIC].
- Nói: "Các dữ liệu này được loại bỏ/che trước khi gọi model khi có thể."
- Mở LinkedIn/Testimonial/Case Study.

## 4. Output Guardrail
"Sau model vẫn scan lại output, vì model có thể tạo claim hoặc làm lộ thông tin."

## 5. Consent
"Learner review → chọn Public/Limited/Private → consent → Datapot approval. AI không tự publish."

## 6. Production
"Prototype này dùng rules để chứng minh workflow. Production sẽ tích hợp enterprise DLP/PII classification và Microsoft ecosystem."