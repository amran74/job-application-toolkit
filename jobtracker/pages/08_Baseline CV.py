import io
import streamlit as st
from lib.db import get_conn, init_db, get_setting, set_setting
from lib.ui import *

st.set_page_config(page_title="Baseline CV", layout="wide")
inject_global_css()
sidebar_brand()

def extract_pdf_text(uploaded_file):
    pdf_bytes = uploaded_file.read()
    if not pdf_bytes:
        return ""

    # Try pypdf first
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        parts = []
        for page in reader.pages:
            txt = page.extract_text() or ""
            if txt.strip():
                parts.append(txt.strip())
        return "\n\n".join(parts).strip()
    except Exception:
        pass

    # Fallback to PyPDF2 if available
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        parts = []
        for page in reader.pages:
            txt = page.extract_text() or ""
            if txt.strip():
                parts.append(txt.strip())
        return "\n\n".join(parts).strip()
    except Exception as e:
        raise RuntimeError(f"Could not extract text from PDF. Install pypdf or PyPDF2. Details: {e}")

conn = get_conn()
init_db(conn)

if "baseline_editor_text" not in st.session_state:
    st.session_state["baseline_editor_text"] = get_setting(conn, "baseline_cv_text") or ""

page_header(
    "Baseline CV",
    "Store the master source material used by the AI CV Generator before job-specific tailoring begins. You can paste it manually or import it from PDF.",
    eyebrow="Core source material",
)

left, right = st.columns([1.15, 0.85], gap="large")

with right:
    section_title("How to use it")
    soft_card(
        "Purpose",
        "This is the raw master CV text the AI uses as source material. Keep it factual, broad enough to cover your real background, and clean enough that the model is not forced to decode chaos.",
    )
    soft_card(
        "Best practice",
        "Import from PDF if you already have a full CV, then clean the extracted text inside the editor. Keep projects, experience, education, skills, and languages readable as plain text.",
    )

    section_title("Import from PDF")
    upload_mode = st.radio(
        "When importing PDF text",
        options=["Replace current text", "Append to current text"],
        index=0,
        key="baseline_pdf_mode",
    )

    uploaded_pdf = st.file_uploader(
        "Upload CV PDF",
        type=["pdf"],
        key="baseline_pdf_upload",
        help="Upload an existing CV PDF and extract its text into the baseline editor.",
    )

    if uploaded_pdf is not None:
        if st.button("Import PDF text", use_container_width=True):
            try:
                extracted = extract_pdf_text(uploaded_pdf)
                if not extracted.strip():
                    st.warning("The PDF was read, but no extractable text was found.")
                else:
                    current = st.session_state.get("baseline_editor_text", "")
                    if upload_mode == "Append to current text" and str(current).strip():
                        st.session_state["baseline_editor_text"] = current.strip() + "\n\n" + extracted.strip()
                    else:
                        st.session_state["baseline_editor_text"] = extracted.strip()
                    st.success("PDF text imported into the editor.")
                    st.rerun()
            except Exception as e:
                st.error(str(e))

with left:
    section_title("Baseline source text")
    form_shell_open()

    baseline_text = st.text_area(
        "Paste or edit your baseline CV",
        value=st.session_state.get("baseline_editor_text", ""),
        height=460,
        placeholder="Paste your full baseline CV text here, or import it from PDF...",
        key="baseline_editor_area",
    )

    st.session_state["baseline_editor_text"] = baseline_text

    c1, c2 = st.columns(2)
    with c1:
        save = st.button("Save baseline CV", type="primary", use_container_width=True)
    with c2:
        reload_saved = st.button("Reload saved version", use_container_width=True)

    form_shell_close()

if reload_saved:
    st.session_state["baseline_editor_text"] = get_setting(conn, "baseline_cv_text") or ""
    st.success("Reloaded saved baseline CV.")
    st.rerun()

if save:
    set_setting(conn, "baseline_cv_text", st.session_state.get("baseline_editor_text", "").strip())
    st.success("Baseline CV saved.")
