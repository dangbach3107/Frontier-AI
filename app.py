import os
import re
import json
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

st.set_page_config(
    page_title="Datapot AI Learning Showcase",
    page_icon="🚀",
    layout="wide",
)

# Helper lấy cấu hình hỗ trợ trực tiếp st.secrets (Streamlit Cloud), .env (Local) và os.environ
def get_config(key, default=""):
    # 1. Thử lấy từ st.secrets (dành cho Streamlit Community Cloud)
    try:
        if key in st.secrets and str(st.secrets[key]).strip():
            return str(st.secrets[key]).strip()
    except Exception:
        pass

    # 2. Thử lấy trực tiếp từ file .env (dành cho máy Local)
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == key:
                    clean_v = v.strip().strip("'\"")
                    if clean_v:
                        return clean_v

    # 3. Thử lấy từ biến môi trường hệ thống
    val = os.getenv(key, "")
    if val:
        return val

    return default




# =========================================================
# 1) PRE-PROCESSING / PRIVACY LAYER
# =========================================================

BLOCK_PATTERNS = {
    "API key / secret": [
        r"\bsk-[A-Za-z0-9_-]{12,}\b",
        r"\b(?:api[_ -]?key|secret[_ -]?key)\s*[:=]\s*[A-Za-z0-9_\-]{8,}\b",
        r"\b(?:access[_ -]?token|refresh[_ -]?token)\s*[:=]\s*[A-Za-z0-9_\-\.]{8,}\b",
    ],
    "Password": [
        r"\b(?:password|passwd|pwd|mật khẩu)\s*[:=]\s*[^\s,;]{4,}\b",
    ],
    "CCCD / ID number": [
        r"(?<!\d)\d{12}(?!\d)",
    ],
    "Bank / card-like number": [
        r"(?<!\d)\d{10,19}(?!\d)",
    ],
}

PII_PATTERNS = {
    "Email": [
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    ],
    "Phone": [
        r"(?<!\d)(?:\+84|0)(?:[\s.-]?\d){8,10}(?!\d)",
    ],
}

BUSINESS_PATTERNS = {
    "Revenue / financial metric": [
        r"(?:doanh\s*thu|revenue|lợi\s*nhuận|profit).{0,80}?\d[\d.,]*\s*(?:tỷ|tr|million|m|billion|bn|%)?",
        r"\b\d[\d.,]*\s*(?:tỷ|tr|million|m|billion|bn)\b",
    ],
    "KPI / internal metric": [
        r"\b(?:KPI|OKR|internal metric|chỉ tiêu nội bộ)\b",
    ],
    "Customer information": [
        r"\b(?:khách hàng|customer|client)\b",
    ],
    "Confidential / internal": [
        r"\b(?:confidential|internal|nội bộ|bí mật)\b",
    ],
    "Unreleased information": [
        r"\b(?:chưa công bố|unreleased|roadmap nội bộ|sắp ra mắt)\b",
    ],
}

CONSENT_FIELDS = {
    "name": "Họ tên",
    "job": "Chức danh",
    "company": "Tên công ty",
    "photo": "Hình ảnh",
    "project": "Project",
    "achievement": "Thành tích / kết quả học tập",
}

def find_matches(text: str, patterns: dict):
    matches = []
    for label, regex_or_list in patterns.items():
        regex_list = regex_or_list if isinstance(regex_or_list, list) else [regex_or_list]
        for regex in regex_list:
            for m in re.finditer(regex, text, flags=re.IGNORECASE | re.DOTALL):
                matches.append({
                    "type": label,
                    "start": m.start(),
                    "end": m.end(),
                    "value": m.group(0),
                })
    return matches

def preprocess(text: str):
    """
    Deterministic pre-processing:
      A. BLOCK: credential / ID-like patterns -> do not send to LLM.
      B. PII: mask email/phone.
      C. BUSINESS: flag + mask obvious sensitive spans.
    Returns sanitized text + risk records.
    """
    risks = []

    block_matches = find_matches(text, BLOCK_PATTERNS)
    for m in block_matches:
        risks.append({
            "severity": "BLOCK",
            "type": m["type"],
            "value": m["value"],
            "action": "BLOCK before LLM",
        })

    # Mask PII locally before any LLM call.
    sanitized = text
    for label, regex_or_list in PII_PATTERNS.items():
        replacement = f"[{label.upper()}]"
        regex_list = regex_or_list if isinstance(regex_or_list, list) else [regex_or_list]
        for regex in regex_list:
            sanitized = re.sub(regex, replacement, sanitized, flags=re.IGNORECASE)

    for label, regex_list in BUSINESS_PATTERNS.items():
        for regex in regex_list:
            for m in re.finditer(regex, sanitized, flags=re.IGNORECASE | re.DOTALL):
                risks.append({
                    "severity": "REVIEW",
                    "type": label,
                    "value": m.group(0)[:160],
                    "action": "MASK + human review",
                })

        # Mask broad business-sensitive phrases, while preserving the rest.
        # This is intentionally conservative for the prototype.
        if label == "Customer information":
            sanitized = re.sub(
                r"\b(?:khách hàng|customer|client)(?:\s+\w+){0,4}",
                "[CUSTOMER_INFO]",
                sanitized,
                flags=re.IGNORECASE,
            )
        elif label == "Confidential / internal":
            sanitized = re.sub(
                r"\b(?:confidential|internal|nội bộ|bí mật)\b",
                "[CONFIDENTIAL_INFO]",
                sanitized,
                flags=re.IGNORECASE,
            )
        elif label == "KPI / internal metric":
            sanitized = re.sub(
                r"\b(?:KPI|OKR|internal metric|chỉ tiêu nội bộ)\b",
                "[INTERNAL_METRIC]",
                sanitized,
                flags=re.IGNORECASE,
            )
        elif label == "Unreleased information":
            sanitized = re.sub(
                r"\b(?:chưa công bố|unreleased|roadmap nội bộ|sắp ra mắt)\b",
                "[UNRELEASED_INFO]",
                sanitized,
                flags=re.IGNORECASE,
            )
        elif label == "Revenue / financial metric":
            sanitized = re.sub(
                r"\b(?:doanh\s*thu|revenue|lợi\s*nhuận|profit)\b.{0,80}?(?=[\.\n]|$)",
                "[BUSINESS_METRIC]",
                sanitized,
                flags=re.IGNORECASE | re.DOTALL,
            )

    # Duplicate removal
    unique = []
    seen = set()
    for r in risks:
        key = (r["severity"], r["type"], r["value"])
        if key not in seen:
            unique.append(r)
            seen.add(key)

    return sanitized, unique

def output_scan(text: str):
    risks = []
    for m in find_matches(text, BLOCK_PATTERNS):
        risks.append(f"BLOCK: {m['type']}")
    for m in find_matches(text, PII_PATTERNS):
        risks.append(f"PII: {m['type']}")
    for label, regex_list in BUSINESS_PATTERNS.items():
        for regex in regex_list:
            if re.search(regex, text, flags=re.IGNORECASE | re.DOTALL):
                risks.append(f"REVIEW: {label}")
                break
    return sorted(set(risks))

# =========================================================
# 2) DEMO GENERATOR / OPTIONAL REAL LLM
# =========================================================

def demo_generate(experience, project, result):
    """
    Demo Mode is deterministic and does NOT call an external model.
    It proves the workflow and UI. A real LLM can be connected below.
    """
    project = project.strip() or "một sản phẩm học tập"
    result = result.strip() or "có cải thiện quy trình làm việc"

    linkedin = f"""Từ việc học đến áp dụng thực tế.

Sau khóa học tại Datapot, tôi đã áp dụng kiến thức vào {project.lower()}.

Điểm thay đổi lớn nhất: {result}

Điều mình thấy giá trị nhất là chuyển kiến thức từ lớp học thành một sản phẩm có thể áp dụng vào công việc.

#Datapot #LearningByDoing #Data"""

    facebook = f"""Mình vừa hoàn thành một bước quan trọng trong quá trình học tại Datapot.

Dự án: {project}
Kết quả: {result}

Điều mình thích nhất là được học theo hướng thực hành và có thể thử nghiệm ngay trên bài toán thực tế."""

    testimonial = f"""“Khóa học giúp tôi chuyển kiến thức thành một sản phẩm thực tế: {project}. 
Kết quả rõ nhất là {result}.”"""

    case_study = f"""CASE STUDY

Bối cảnh
Học viên muốn áp dụng kiến thức đã học vào một bài toán thực tế.

Sản phẩm
{project}

Kết quả
{result}

Bài học
Học qua dự án giúp rút ngắn khoảng cách giữa kiến thức và công việc thực tế."""

    showcase = f"""PROJECT SHOWCASE

{project}

{result}

Một sản phẩm học tập tiêu biểu từ cộng đồng học viên Datapot."""

    return {
        "LinkedIn": linkedin,
        "Facebook": facebook,
        "Testimonial": testimonial,
        "Case Study": case_study,
        "Project Showcase": showcase,
    }

def llm_generate(sanitized_text, project, result):
    """
    OpenAI-compatible endpoint (YEScale, OpenAI, Azure OpenAI proxy, etc.).
    Configuration is read strictly from backend (st.secrets, .env, or env vars).
    """
    base_url = get_config("LLM_BASE_URL", "https://api.yescale.io/v1").rstrip("/")
    api_key = get_config("LLM_API_KEY", "").strip()
    model = get_config("LLM_MODEL", "gemini-2.5-flash").strip()

    if not api_key:
        return None, "Demo Mode"

    system = """
You are Datapot's AI Learning Showcase content assistant.
Use ONLY information present in the sanitized input.
Do NOT reconstruct, infer, guess, or invent masked data.
Do NOT invent names, companies, customers, revenue, KPI, achievements, or claims.
Create concise, authentic marketing content in Vietnamese.
Return strict JSON with keys:
LinkedIn, Facebook, Testimonial, Case Study, Project Showcase.
"""

    user = f"""
Sanitized learner experience:
{sanitized_text}

Project:
{project}

Result:
{result}
"""

    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
            },
            timeout=60,
        )
        response.raise_for_status()
        raw_text = response.json()["choices"][0]["message"]["content"].strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            data = json.loads(cleaned)
        except Exception:
            match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
            if match:
                data = json.loads(match.group(0))
            else:
                raise ValueError(f"Không thể parse JSON từ kết quả model: {raw_text[:200]}")
        return data, f"LLM Mode ({model})"
    except Exception as exc:
        return None, f"Demo Mode (Lỗi gọi LLM: {exc})"

# =========================================================
# 3) UI
# =========================================================

st.title("🚀 AI Learning Showcase")
st.caption(
    "Prototype: Learner → Pre-processing → AI → Output Guardrail → Review → Consent → Datapot Approval"
)

with st.sidebar:
    st.header("Privacy-by-design")
    st.write("🔴 BLOCK — credential / CCCD / secret")
    st.write("🟠 REVIEW — business sensitive")
    st.write("🟡 CONSENT — personal/public identity")
    st.write("🟢 ALLOW — learning experience")
    st.divider()

    backend_key = get_config("LLM_API_KEY", "")
    backend_model = get_config("LLM_MODEL", "gemini-2.5-flash")
    backend_url = get_config("LLM_BASE_URL", "https://api.yescale.io/v1")

    @st.cache_data(ttl=300, show_spinner=False)
    def test_connection(key, url, model):
        try:
            r = requests.post(
                f"{url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
                timeout=10,
            )
            if r.status_code == 200:
                return True, "Kết nối 200 OK"
            return False, f"Mã lỗi {r.status_code}"
        except Exception as e:
            return False, str(e)

    if backend_key:
        ok, msg = test_connection(backend_key, backend_url, backend_model)
        if ok:
            st.success(f"🟢 **AI Engine: Đã kết nối**\n\n• Model: `{backend_model}`\n\n• Health check: `{msg}`")
        else:
            st.warning(f"⚠️ **API Key chưa khả dụng**\n\n{msg}")
    else:
        st.info("ℹ️ **Chế độ: Demo Mode**\n\n*(Chưa tìm thấy API Key trong Secrets/Environment)*")


st.subheader("1. Learner input")

c1, c2 = st.columns(2)

with c1:
    experience = st.text_area(
        "Trải nghiệm / câu chuyện",
        value=(
            "Tôi là Nguyễn Văn A, Data Analyst tại Công ty ABC. "
            "Tôi xây dashboard Power BI cho khách hàng XYZ. "
            "Dashboard giúp giảm thời gian báo cáo từ 3 giờ xuống 30 phút. "
            "Email: nguyenvana@gmail.com."
        ),
        height=170,
    )
    project = st.text_input("Project", value="Power BI sales dashboard")

with c2:
    result = st.text_area(
        "Kết quả / thay đổi",
        value="Quy trình tổng hợp báo cáo nhanh hơn đáng kể và dễ theo dõi hơn.",
        height=170,
    )

    st.markdown("**Quyền sử dụng (Consent)**")
    consent = {
        key: st.checkbox(label, value=False)
        for key, label in CONSENT_FIELDS.items()
    }

run = st.button("▶ Run prototype", type="primary", use_container_width=True)

if run:
    source_text = "\n".join([experience, project, result])

    sanitized_text, risks = preprocess(source_text)

    # Hard stop if credentials are present.
    hard_block = [r for r in risks if r["severity"] == "BLOCK"]

    st.session_state["source"] = source_text
    st.session_state["sanitized"] = sanitized_text
    st.session_state["risks"] = risks
    st.session_state["hard_block"] = hard_block

    if hard_block:
        st.session_state["generated"] = None
        st.session_state["mode"] = "BLOCKED"
    else:
        generated, mode = llm_generate(sanitized_text, project, result)
        if generated is None:
            generated = demo_generate(experience, project, result)
        st.session_state["generated"] = generated
        st.session_state["mode"] = mode

if "sanitized" in st.session_state:
    st.subheader("2. Pre-processing — trước khi gọi LLM")

    left, right = st.columns(2)
    with left:
        st.markdown("**RAW INPUT**")
        st.code(st.session_state["source"], language="text")

    with right:
        st.markdown("**SANITIZED INPUT → LLM**")
        st.code(st.session_state["sanitized"], language="text")

    risks = st.session_state["risks"]

    if st.session_state["hard_block"]:
        st.error(
            "⛔ BLOCK: Phát hiện dữ liệu không được phép gửi tới LLM. "
            "Hãy xóa/che credential hoặc định danh nhạy cảm rồi chạy lại."
        )
        for r in st.session_state["hard_block"]:
            st.write(f"🔴 {r['type']}: `{r['value']}`")
    elif risks:
        st.warning("⚠️ Có dữ liệu cần review/consent trước khi publish.")
        for r in risks:
            icon = "🟠" if r["severity"] == "REVIEW" else "🔵"
            st.write(f"{icon} {r['type']} → {r['action']}")
    else:
        st.success("✅ Pre-processing: không phát hiện risk theo rule prototype.")

if st.session_state.get("generated"):
    st.subheader("3. AI-generated content")

    st.caption(f"Generation mode: **{st.session_state.get('mode', 'Demo Mode')}**")

    generated = st.session_state["generated"]
    tabs = st.tabs(list(generated.keys()))

    for tab, key in zip(tabs, generated.keys()):
        with tab:
            st.text_area(
                key,
                value=str(generated[key]),
                height=220,
                key=f"content_{key}",
            )

    st.subheader("4. Output Guardrail")

    edited_outputs = {}
    for key in generated.keys():
        edited_outputs[key] = st.session_state.get(
            f"content_{key}", str(generated[key])
        )

    combined_output = "\n".join(edited_outputs.values())
    output_risks = output_scan(combined_output)

    if output_risks:
        st.error("⛔ Output còn risk — chưa được phép publish.")
        for r in output_risks:
            st.write("•", r)
    else:
        st.success("✅ Output guardrail passed.")

    st.subheader("5. Learner review → Consent → Datapot approval")

    share_level = st.radio(
        "Mức chia sẻ",
        ["Public", "Limited — ẩn thông tin nhạy cảm", "Private — nội bộ"],
        horizontal=True,
    )

    reviewed = st.checkbox("Tôi đã review và xác nhận nội dung AI tạo ra.")
    consent_ok = any(consent.values())

    if share_level == "Public" and not consent.get("name", False):
        st.info("Public: nên yêu cầu consent cho Họ tên/identity trước khi xuất bản.")

    if st.button("✅ Submit to Datapot", use_container_width=True):
        if output_risks:
            st.error("Chưa submit: output guardrail chưa đạt.")
        elif not reviewed:
            st.error("Chưa submit: cần Learner Review.")
        elif not consent_ok and share_level != "Private — nội bộ":
            st.error("Chưa submit: cần ít nhất một consent phù hợp với mức chia sẻ.")
        else:
            payload = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "share_level": share_level,
                "consent": consent,
                "content": edited_outputs,
                "status": "Pending Datapot Review",
            }

            out = Path("submission_demo.json")
            out.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            st.success(
                "🎉 Submitted — status: **Pending Datapot Review**. "
                "Production có thể thay bước này bằng Power Automate → Dataverse/SharePoint."
            )

st.divider()
st.caption(
    "Prototype scope: pre-processing + sanitization + content generation + "
    "output guardrail + consent + approval handoff. Production cần enterprise DLP, "
    "RBAC/SSO, audit log, stronger PII classifiers và policy enforcement."
)