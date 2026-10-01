# Datapot AI Learning Showcase — Prototype v2

## Điểm mới của v2

Prototype này được sửa theo hướng **privacy-by-design**:

Raw learner input
→ Pre-processing
→ Data classification
→ Block / Mask / Review
→ Sanitized input
→ LLM
→ Output guardrail
→ Learner review
→ Consent
→ Datapot approval

Quan trọng: **LLM không nhận raw sensitive data khi prototype phát hiện được dữ liệu đó.**

## 1. Chạy Demo Mode

Yêu cầu Python 3.10+.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Demo Mode không cần API key. Mục đích là trình diễn end-to-end workflow. Phần "AI-generated content" trong Demo Mode là deterministic template generator, KHÔNG gọi model bên ngoài.

## 2. Kết nối LLM thật

App hỗ trợ OpenAI-compatible Chat Completions endpoint.

macOS/Linux:

```bash
export LLM_BASE_URL="https://your-endpoint/v1"
export LLM_API_KEY="your-key"
export LLM_MODEL="your-model"
streamlit run app.py
```

Windows PowerShell:

```powershell
$env:LLM_BASE_URL="https://your-endpoint/v1"
$env:LLM_API_KEY="your-key"
$env:LLM_MODEL="your-model"
streamlit run app.py
```

Khi đủ 3 biến trên, app sẽ:
1. pre-process và sanitize input
2. gửi sanitized input tới LLM
3. scan output lần 2

## 3. Kịch bản demo 3–5 phút

### 20 giây — Problem
"Học viên có trải nghiệm nhưng ngại biến nó thành content. Datapot và Marketing thì cần content thật."

### 30 giây — Privacy insight
"Em không cho raw data đi thẳng vào LLM. Có một pre-processing layer trước model."

### 1–2 phút — Demo
1. Giữ sample input.
2. Bấm Run Prototype.
3. Chỉ ra RAW INPUT.
4. Chỉ ra SANITIZED INPUT:
   - email → [EMAIL]
   - customer → [CUSTOMER_INFO]
   - business metric → [BUSINESS_METRIC]
5. Mở các tab LinkedIn / Facebook / Testimonial / Case Study / Project Showcase.

### 30–60 giây — Guardrail
"Output được scan lại sau LLM. Nếu còn credential/PII/business-sensitive pattern thì chưa publish."

### 30 giây — Human control
"Learner review → consent → Datapot approval. AI không tự publish."

### 30 giây — Production
"Production có thể thay rule prototype bằng Microsoft Purview/DLP, PII/NER service, Azure OpenAI/Copilot, Dataverse và Power Automate."

## 4. Bảng classification trong prototype

### BLOCK
- API key / secret
- password
- CCCD-like number
- bank/card-like number

→ block trước LLM.

### REVIEW
- revenue / financial metric
- KPI / internal metric
- customer information
- confidential/internal
- unreleased information

→ mask/flag + human review.

### CONSENT
- name
- job title
- company
- photo
- project
- achievement

→ chỉ dùng theo quyền học viên chọn.

## 5. Production architecture

```text
Microsoft Forms / Web
        ↓
Power Automate
        ↓
DLP / PII / NER / Policy Engine
        ↓
Sanitized Input
        ↓
Azure OpenAI / Copilot
        ↓
Output Guardrail
        ↓
Dataverse / SharePoint
        ↓
Learner Review + Consent
        ↓
Datapot Approval
        ↓
Power Pages / Social
        ↓
Power BI
```

## 6. Câu nói khi phỏng vấn

> "I designed the prototype with a pre-processing layer, because detecting sensitive data after sending raw data to an LLM would be too late. The model should receive the minimum sanitized information required for content generation."

## 7. Giới hạn của prototype

Rule/regex chỉ là MVP demonstration. Production cần:
- Microsoft Purview / enterprise DLP
- stronger PII/NLP classifiers
- RBAC/SSO
- audit trail
- encryption
- retention policy
- approval policy
- monitoring and cost controls
- LMS/CRM integration