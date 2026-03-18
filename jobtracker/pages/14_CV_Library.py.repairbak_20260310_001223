import os
import shutil
import sqlite3
from datetime import datetime

import streamlit as st
import pandas as pd

from lib.db import get_conn, init_db, DB_PATH

st.set_page_config(page_title="CV Library", layout="wide")
st.title("CV Library")
st.caption("Store past CV PDFs so you can reuse them instead of re-inventing your life every time.")

conn = get_conn()
init_db(conn)


LIB_DIR = os.path.join("jobtracker", "exports", "cv_library")
os.makedirs(LIB_DIR, exist_ok=True)

def utc_now():
    return datetime.utcnow().isoformat(timespec="seconds")

def safe_name(s: str) -> str:
    s = (s or "").strip()
    keep = []
    for ch in s:
        if ch.isalnum() or ch in ("_", "-", " "):
            keep.append(ch)
    return ("".join(keep).strip().replace(" ", "_") or "cv")[:40]

def add_to_library(src_path: str, label: str, source: str, job_id=None, notes=""):
    src_path = (src_path or "").strip()
    if not src_path or not os.path.exists(src_path):
        raise FileNotFoundError("Source file not found.")

    label = (label or "").strip()
    if not label:
        label = os.path.basename(src_path)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = safe_name(label)
    dst_name = f"{base}_{stamp}.pdf"
    dst_path = os.path.join(LIB_DIR, dst_name)

    shutil.copyfile(src_path, dst_path)

    conn.execute(
        "INSERT INTO cv_library(created_at, label, source, job_id, file_path, notes) VALUES (?,?,?,?,?,?);",
        (utc_now(), label, source, job_id, dst_path, notes or "")
    )
    conn.commit()
    return dst_path

def fetch_library():
    return pd.read_sql_query("SELECT * FROM cv_library ORDER BY datetime(created_at) DESC;", conn)

def delete_library_item(item_id: int):
    row = conn.execute("SELECT file_path FROM cv_library WHERE id=?;", (item_id,)).fetchone()
    if row:
        fp = row[0]
        try:
            if fp and os.path.exists(fp):
                os.remove(fp)
        except Exception:
            pass
    conn.execute("DELETE FROM cv_library WHERE id=?;", (item_id,))
    conn.commit()

def ai_cv_rows():
    # Pull AI CV pdfs that exist, with job info
    q = """
    SELECT v.id as version_id,
           v.job_id,
           j.company,
           j.role,
           v.created_at,
           v.model,
           v.archetype,
           v.tone,
           v.length,
           v.cv_pdf_path
    FROM cv_versions v
    LEFT JOIN jobs j ON j.id = v.job_id
    WHERE v.cv_pdf_path IS NOT NULL AND v.cv_pdf_path != ''
    ORDER BY datetime(v.created_at) DESC
    """
    try:
        df = pd.read_sql_query(q, conn)
        return df
    except Exception:
        return pd.DataFrame()

def scan_export_pdfs():
    # reasonable scan locations only
    paths = []
    candidates = [
        os.path.join("jobtracker", "exports"),
        ".",  # in case manual export dumped to root
    ]
    seen = set()
    for root in candidates:
        if not os.path.exists(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            # avoid scanning the library inside itself twice
            if os.path.normpath(dirpath).startswith(os.path.normpath(LIB_DIR)):
                continue
            for fn in filenames:
                if fn.lower().endswith(".pdf"):
                    fp = os.path.abspath(os.path.join(dirpath, fn))
                    if fp not in seen:
                        seen.add(fp)
                        paths.append(fp)
    return paths

st.subheader("Add existing PDFs into the library")

tab1, tab2 = st.tabs(["From AI CV History", "From exported PDFs (scan)"])

with tab1:
    df_ai = ai_cv_rows()
    if df_ai.empty:
        st.info("No AI CV PDFs found yet. Generate one in AI CV Generator first.")
    else:
        df_ai_display = df_ai.copy()
        df_ai_display["job"] = df_ai_display.apply(lambda r: f"#{int(r.job_id)} | {r.company} - {r.role}", axis=1)
        pick = st.selectbox("Select an AI CV PDF", df_ai_display["job"] + " | " + df_ai_display["created_at"])
        idx = df_ai_display.index[df_ai_display["job"] + " | " + df_ai_display["created_at"] == pick][0]
        row = df_ai_display.loc[idx]

        label = st.text_input("Library label", value=f'{row["company"]} - {row["role"]} ({row["archetype"]})')
        notes = st.text_input("Notes (optional)", value="")

        if st.button("Add selected AI CV to Library", type="primary"):
            src = row["cv_pdf_path"]
            if not os.path.exists(src):
                st.error(f"PDF path not found on disk: {src}")
            else:
                dst = add_to_library(src, label=label, source="ai", job_id=int(row["job_id"]), notes=notes)
                st.success(f"Saved into library: {dst}")

with tab2:
    pdfs = scan_export_pdfs()
    if not pdfs:
        st.info("No PDFs found in exports/root yet.")
    else:
        pick = st.selectbox("Select a PDF to import", pdfs)
        label = st.text_input("Library label", value=os.path.basename(pick))
        notes = st.text_input("Notes (optional)", value="")
        if st.button("Add selected PDF to Library", type="primary"):
            try:
                dst = add_to_library(pick, label=label, source="imported", job_id=None, notes=notes)
                st.success(f"Saved into library: {dst}")
            except Exception as e:
                st.error(str(e))

st.divider()
st.subheader("Your CV Library")

lib = fetch_library()
if lib.empty:
    st.info("Library is empty. Add a CV above.")
else:
    # show table
    view = lib.copy()
    view["created_at"] = pd.to_datetime(view["created_at"], errors="coerce")
    st.dataframe(
        view[["id","created_at","label","source","job_id","notes","file_path"]],
        use_container_width=True,
        hide_index=True
    )

    st.write("Download / Delete")
    pick_id = st.selectbox("Pick library item", view["id"].tolist())
    item = view[view["id"] == pick_id].iloc[0]
    fp = item["file_path"]

    c1, c2 = st.columns([1,1])
    with c1:
        if fp and os.path.exists(fp):
            with open(fp, "rb") as f:
                st.download_button("Download PDF", f, file_name=os.path.basename(fp), mime="application/pdf")
        else:
            st.error("File missing on disk (was deleted or moved).")
    with c2:
        if st.button("Delete from library", type="secondary"):
            delete_library_item(int(pick_id))
            st.success("Deleted. Gone. Like recruiter replies.")
            st.rerun()
