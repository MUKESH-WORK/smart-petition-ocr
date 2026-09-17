import os
import tempfile
import json
import requests
import streamlit as st

# Ensure all uploads & temp buffers use E: drive with 30GB+ free space instead of full C: drive
_workspace_temp = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "temp_cache"))
os.makedirs(_workspace_temp, exist_ok=True)
os.environ["TEMP"] = _workspace_temp
os.environ["TMP"] = _workspace_temp
os.environ["TMPDIR"] = _workspace_temp
tempfile.tempdir = _workspace_temp

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
GRIEVANCE_API = f"{API_BASE}/grievance"

st.set_page_config(
    page_title="Petition Document Assistant | AI Administrative Co-Pilot",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS matching the exact design of the 3 screenshots
st.markdown("""
<style>
    /* Global Canvas */
    .stApp {
        background-color: #f8fafc;
        color: #1e293b;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* Top Orange Header */
    .copilot-header {
        background: linear-gradient(90deg, #ea580c 0%, #f97316 100%);
        padding: 12px 24px;
        margin: -6rem -4rem 1.5rem -4rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
    }
    .header-left {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .header-title {
        font-size: 16px;
        font-weight: 700;
        margin: 0;
        line-height: 1.2;
    }
    .header-sub {
        font-size: 12px;
        color: #ffedd5;
        margin: 0;
    }
    .lang-badge {
        background: rgba(255,255,255,0.2);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        display: inline-flex;
        gap: 6px;
    }
    .officer-badge {
        background: rgba(0,0,0,0.2);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Upload Box (Screenshot 1) */
    .upload-card {
        border: 2px dashed #fdba74;
        background: #fffaf5;
        border-radius: 12px;
        padding: 36px 24px;
        text-align: center;
        max-width: 540px;
        margin: 20px auto;
    }
    .upload-icon {
        font-size: 38px;
        color: #ea580c;
        margin-bottom: 8px;
    }
    .upload-title {
        font-size: 18px;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 4px;
    }
    .upload-subtitle {
        font-size: 13px;
        color: #64748b;
        margin-bottom: 16px;
    }

    /* Summary Card (Screenshot 2) */
    .summary-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #f97316;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .summary-tag {
        font-size: 12px;
        font-weight: 800;
        color: #0369a1;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }
    .summary-text {
        font-size: 14px;
        color: #334155;
        line-height: 1.6;
        margin: 0;
    }

    /* Full Petition Details Card (Screenshot 3) */
    .details-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 18px 20px;
        margin: 12px 0;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    .details-card-header {
        font-size: 13px;
        font-weight: 800;
        color: #1e293b;
        letter-spacing: 0.5px;
        border-bottom: 1px solid #f1f5f9;
        padding-bottom: 8px;
        margin-bottom: 14px;
    }
    .field-label {
        font-size: 12px;
        font-weight: 700;
        color: #475569;
        margin-bottom: 4px;
    }
    .field-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
        color: #1e293b;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .copy-btn {
        color: #64748b;
        font-size: 11px;
        cursor: pointer;
        padding: 2px 6px;
        border-radius: 4px;
        background: #ffffff;
        border: 1px solid #cbd5e1;
    }

    /* Assistant Header in Chat */
    .assistant-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 8px;
    }
    .assistant-badge {
        background: #0284c7;
        color: white;
        padding: 2px 6px;
        border-radius: 50%;
        font-size: 10px;
    }

    /* Toast Notification (Screenshot 2) */
    .toast-pill {
        background: #0f172a;
        color: #f8fafc;
        padding: 10px 18px;
        border-radius: 8px;
        font-size: 13px;
        display: inline-block;
        margin-top: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Top File Bar */
    .file-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 0;
        border-bottom: 1px solid #e2e8f0;
        margin-bottom: 16px;
    }
    .file-name {
        font-size: 14px;
        font-weight: 600;
        color: #334155;
        display: flex;
        align-items: center;
        gap: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Top Bar (Header)
st.markdown("""
<div class="copilot-header">
    <div class="header-left">
        <span style="font-size: 24px;">🏛️</span>
        <div>
            <div class="header-title">AI Administrative Co-Pilot</div>
            <div class="header-sub">Government Grievance Pre-Processing</div>
        </div>
    </div>
    <div style="display: flex; align-items: center; gap: 16px;">
        <div class="lang-badge">
            <span style="background: white; color: #ea580c; padding: 2px 6px; border-radius: 10px;">English</span>
            <span>தமிழ்</span>
        </div>
        <div class="officer-badge">
            <span>👤</span>
            <div>
                <b>S. Ramanathan</b><br>
                <span style="font-size: 10px; opacity: 0.9;">Tahsildar • Grievance Cell</span>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# State Init
if "active_source_id" not in st.session_state:
    st.session_state.active_source_id = None
if "active_filename" not in st.session_state:
    st.session_state.active_filename = None
if "active_summary" not in st.session_state:
    st.session_state.active_summary = None
if "active_draft" not in st.session_state:
    st.session_state.active_draft = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "show_toast" not in st.session_state:
    st.session_state.show_toast = False

# Sidebar Navigation (Screenshot 1)
with st.sidebar:
    st.markdown("### 🏛️ Navigation")
    st.button("📄 GDP Assistant\nGrievance Processing", use_container_width=True, type="primary")
    
    st.divider()
    st.markdown("### 📂 Processed Petitions")
    try:
        hist_res = requests.get(f"{GRIEVANCE_API}/history", timeout=5)
        if hist_res.status_code == 200:
            petitions_list = hist_res.json()
            if petitions_list:
                for p in petitions_list:
                    p_name_lbl = p.get('petitioner_name') or 'Ready'
                    p_label = f"📄 {p.get('file_name', 'Petition')[:20]} ({p_name_lbl})"
                    if st.button(p_label, key=f"hist_{p['source_id']}", use_container_width=True):
                        sid = str(p['source_id'])
                        st.session_state.active_source_id = sid
                        st.session_state.active_filename = p.get('file_name', 'Petition')
                        st.session_state.show_toast = True
                        d_res = requests.get(f"{GRIEVANCE_API}/{sid}/draft")
                        if d_res.status_code == 200:
                            d = d_res.json()
                            st.session_state.active_draft = d
                            st.session_state.active_summary = d.get("description") or "மனுதாரர் கோரிக்கை மனு சமர்ப்பித்துள்ளார்."
                        st.session_state.messages = []
                        st.rerun()
            else:
                st.caption("No petitions uploaded yet.")
    except Exception:
        st.caption("Backend offline or initializing.")

    st.divider()
    st.caption("SYSTEM")
    if st.button("🕒 Audit Logs", use_container_width=True):
        st.info("System logging active in PostgreSQL partitioned tables.")
    if st.button("⚙️ Settings", use_container_width=True):
        st.info("Language: Bilingual (English / Tamil)\nEngine: PostgreSQL 16 Hybrid OCR + LLM")
    
    st.divider()
    if st.session_state.active_source_id:
        st.caption(f"Active ID: `{st.session_state.active_source_id[:8]}...`")
        if st.button("🔄 Reset / New Petition", use_container_width=True):
            st.session_state.active_source_id = None
            st.session_state.active_filename = None
            st.session_state.active_summary = None
            st.session_state.active_draft = None
            st.session_state.messages = []
            st.session_state.show_toast = False
            st.rerun()

# ==============================================================================
# FLOW 1: UPLOAD SCREEN (Screenshot 1)
# ==============================================================================
if not st.session_state.active_source_id:
    st.markdown("<div style='text-align: center; margin-top: 30px;'><span style='font-size: 40px;'>🏛️</span></div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; margin-bottom: 2px; color: #1e293b;'>Petition Document Assistant</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b; font-size: 14px;'>Upload or scan a petition to begin.</p>", unsafe_allow_html=True)

    st.markdown("""
    <div class="upload-card">
        <div class="upload-icon">☁️</div>
        <div class="upload-title">Upload Petition</div>
        <div class="upload-subtitle">Drag & drop your document here</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        uploaded_file = st.file_uploader(
            "Browse Document (PDF • JPG • PNG • WEBP)",
            type=["pdf", "jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed"
        )
        st.caption("Supported formats: PDF • JPG • PNG • WEBP")
        
        if uploaded_file is not None:
            if st.button("🚀 Process Petition Document", type="primary", use_container_width=True):
                with st.spinner("Processing OCR, extracting petition details & generating summary..."):
                    try:
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "image/png")}
                        data = {"officer_id": "DRO_OFFICER_DEFAULT", "process_now": "true"}
                        r = requests.post(f"{GRIEVANCE_API}/upload", files=files, data=data, timeout=180)
                        if r.status_code == 200:
                            res = r.json()
                            sid = str(res["source_id"])
                            st.session_state.active_source_id = sid
                            st.session_state.active_filename = uploaded_file.name
                            st.session_state.show_toast = True

                            # Fetch Draft / Details
                            d_res = requests.get(f"{GRIEVANCE_API}/{sid}/draft")
                            if d_res.status_code == 200:
                                d = d_res.json()
                                st.session_state.active_draft = d
                                st.session_state.active_summary = d.get("description") or "The petitioner submitted a formal grievance request for administrative review and action."
                            
                            st.rerun()
                        else:
                            st.error(f"Upload failed: {r.text}")
                    except Exception as e:
                        st.error(f"Connection error: {e}")

# ==============================================================================
# FLOW 2 & 3: PROCESSED PETITION, SUMMARY & ASSISTANT (Screenshot 2 & 3)
# ==============================================================================
else:
    sid = st.session_state.active_source_id
    d = st.session_state.active_draft or {}
    fname = st.session_state.active_filename or d.get("file_name") or "Petition Document"
    summary_txt = st.session_state.active_summary or d.get("description") or "மனுதாரர் நிர்வாக நடவடிக்கை கோரி மனு சமர்ப்பித்துள்ளார்."

    # File Bar (Screenshot 2 & 3 top)
    col_fb1, col_fb2 = st.columns([3, 1])
    with col_fb1:
        st.markdown(f"<div class='file-bar'><div class='file-name'>📄 {fname}</div></div>", unsafe_allow_html=True)
    with col_fb2:
        if st.button("🔄 New Petition"):
            st.session_state.active_source_id = None
            st.session_state.active_filename = None
            st.session_state.active_summary = None
            st.session_state.active_draft = None
            st.session_state.messages = []
            st.session_state.show_toast = False
            st.rerun()

    # Summary Card (Screenshot 2)
    st.markdown(f"""
    <div class="summary-card">
        <div class="summary-tag">SUMMARY</div>
        <p class="summary-text">{summary_txt}</p>
    </div>
    """, unsafe_allow_html=True)

    # Toast banner on first completion (Screenshot 2 bottom right)
    if st.session_state.show_toast:
        st.markdown(f"""
        <div style="text-align: right; margin-bottom: 12px;">
            <span class="toast-pill">Analysis complete for {fname}</span>
        </div>
        """, unsafe_allow_html=True)

    # Render Chat History
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"""
            <div style="text-align: right; margin: 12px 0;">
                <span style="background: #1e3a8a; color: white; padding: 8px 16px; border-radius: 18px; font-size: 14px; display: inline-block;">
                    {msg["content"]}
                </span>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Assistant Response
            if msg.get("is_details_card"):
                # Render Full Petition Details Card (Screenshot 3)
                p_name = d.get("petitioner_name") or "-"
                p_phone = d.get("phone") or "-"
                p_addr = d.get("address") or "-"
                p_grievance = d.get("description") or summary_txt or "-"
                loc_list = [v for v in [d.get('village'), d.get('taluk'), d.get('district')] if v]
                p_loc = ", ".join(loc_list) if loc_list else "-"
                p_ref = d.get("dro_grievance_id") or d.get("ref_number") or "-"
                p_dept = d.get("department") or "-"
                p_action = d.get("relief_sought") or d.get("description") or "மனுவின் மீது உரிய துறை அலுவலர் விசாரணை மேற்கொண்டு தீர்வு காணுதல்."

                st.markdown(f"""
                <div class="assistant-header">
                    <span class="assistant-badge">🤖</span>
                    <span>Petition Assistant</span>
                    <span style="color: #94a3b8; font-weight: 400; font-size: 11px;">12:34 PM</span>
                </div>
                <div class="details-card">
                    <div class="details-card-header">FULL PETITION DETAILS</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <div class="field-label">Petitioner Name</div>
                            <div class="field-box"><span>{p_name}</span><span class="copy-btn">📋 Copy</span></div>
                        </div>
                        <div>
                            <div class="field-label">Phone Number</div>
                            <div class="field-box"><span>{p_phone}</span><span class="copy-btn">📋 Copy</span></div>
                        </div>
                    </div>
                    <div>
                        <div class="field-label">Address</div>
                        <div class="field-box"><span>{p_addr}</span><span class="copy-btn">📋 Copy</span></div>
                    </div>
                    <div>
                        <div class="field-label">Main Grievance</div>
                        <div class="field-box"><span>{p_grievance}</span><span class="copy-btn">📋 Copy</span></div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <div class="field-label">Location</div>
                            <div class="field-box"><span>{p_loc}</span><span class="copy-btn">📋 Copy</span></div>
                        </div>
                        <div>
                            <div class="field-label">Reference Number</div>
                            <div class="field-box"><span>{p_ref}</span><span class="copy-btn">📋 Copy</span></div>
                        </div>
                    </div>
                    <div>
                        <div class="field-label">Suggested Department</div>
                        <div class="field-box"><span>{p_dept}</span><span class="copy-btn">📋 Copy</span></div>
                    </div>
                    <div>
                        <div class="field-label">Requested Action</div>
                        <div class="field-box"><span>{p_action}</span><span class="copy-btn">📋 Copy</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="assistant-header">
                    <span class="assistant-badge">🤖</span>
                    <span>Petition Assistant</span>
                </div>
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; font-size: 14px; margin-bottom: 12px;">
                    {msg["content"]}
                </div>
                """, unsafe_allow_html=True)

    # Suggestion Chips (Screenshot 2 & 3)
    st.markdown("<div style='margin-top: 15px;'>", unsafe_allow_html=True)
    chip_cols = st.columns([1.2, 1.4, 1.8, 1.6, 1.2])
    selected_chip = None
    
    if chip_cols[0].button("📋 Full Details", use_container_width=True):
        selected_chip = "Give me the full details."
    if chip_cols[1].button("⚡ Summarize in one line", use_container_width=True):
        selected_chip = "Summarize the grievance in one single sentence."
    if chip_cols[2].button("🔍 Explain the grievance", use_container_width=True):
        selected_chip = "Explain the grievance in detail with all background and claims."
    if chip_cols[3].button("🏛️ Which department?", use_container_width=True):
        selected_chip = "Which government department and responsible officer should handle this grievance?"
    if chip_cols[4].button("🛠️ What action?", use_container_width=True):
        selected_chip = "What exact administrative action is requested in this petition?"

    st.markdown("</div>", unsafe_allow_html=True)

    # Chat input
    user_input = st.chat_input("Ask anything about this petition...")
    query = selected_chip or user_input

    if query:
        st.session_state.show_toast = False
        st.session_state.messages.append({"role": "user", "content": query})

        if "full detail" in query.lower():
            st.session_state.messages.append({"role": "assistant", "content": "", "is_details_card": True})
            st.rerun()
        else:
            with st.spinner("Analyzing petition..."):
                try:
                    r = requests.post(
                        f"{GRIEVANCE_API}/{sid}/chat",
                        json={"question": query, "top_k": 4},
                        stream=True,
                        timeout=30
                    )
                    full_resp = ""
                    for line in r.iter_lines():
                        if line:
                            obj = json.loads(line)
                            if "delta" in obj:
                                full_resp += obj["delta"]
                    if not full_resp:
                        full_resp = f"Based on the petition, {d.get('description', summary_txt)}"
                    st.session_state.messages.append({"role": "assistant", "content": full_resp, "is_details_card": False})
                    st.rerun()
                except Exception as e:
                    fallback_resp = f"Based on the petition context: {d.get('description', summary_txt)}"
                    st.session_state.messages.append({"role": "assistant", "content": fallback_resp, "is_details_card": False})
                    st.rerun()
