import streamlit as st
from pypdf import PdfReader
from lib.db import get_conn, init_db, set_setting, get_setting

st.set_page_config(page_title="Baseline CV", layout="wide")
st.title("Baseline CV (store once)")
st.caption("Upload/paste your baseline CV once. The AI generator will auto-load it from DB.")

def read_pdf_text(uploaded_file) -> str:
    try:
        reader = PdfReader(uploaded_file)
        parts = []
        for p in reader.pages:
            t = p.extract_text() or ""
            if t.strip():
                parts.append(t)
        return "\n".join(parts).strip()
    except Exception:
        return ""

conn = get_conn()
init_db(conn)

existing = get_setting(conn, "baseline_cv_text")

uploaded = st.file_uploader("Upload baseline CV (PDF)", type=["pdf"])
extracted = read_pdf_text(uploaded) if uploaded else ""

text = st.text_area("Baseline CV text", value=(extracted or existing), height=360)

c1, c2 = st.columns(2)
with c1:
    if st.button("Save baseline CV", type="primary"):
        if not text.strip():
            st.error("Nothing to save.")
        else:
            set_setting(conn, "baseline_cv_text", text.strip())
            st.success("Saved. Now the AI page won’t nag you to paste this every time.")
with c2:
    if st.button("Clear saved baseline"):
        set_setting(conn, "baseline_cv_text", "")
        st.warning("Cleared.")
