
﻿import streamlit as st
import pandas as pd
import os, shutil
from datetime import datetime
from lib.db import DB_PATH, get_conn, init_db, fetch_jobs, upsert_job

st.set_page_config(page_title="Import & Backup", layout="wide")

inject_global_css()
sidebar_brand()
st.title("Import & Backup")
st.caption("Because losing your DB is a spiritual experience you don't need.")

conn = get_conn()
init_db(conn)
df = fetch_jobs(conn)

st.subheader("Export jobs to CSV")
if df.empty:
    st.info("No jobs to export.")
else:
    csv = df.copy()
    # convert datetimes to strings for export
    for col in ["created_at","date_interested","date_applied","date_outcome","next_followup","last_update"]:
        if col in csv.columns:
            csv[col] = csv[col].astype(str)
    st.download_button("Download jobs.csv", csv.to_csv(index=False).encode("utf-8"), file_name="jobs.csv", mime="text/csv")

st.divider()
st.subheader("Import jobs from CSV (append)")
uploaded = st.file_uploader("Upload jobs.csv", type=["csv"])
if uploaded:
    imp = pd.read_csv(uploaded)
    st.write("Preview:")
    st.dataframe(imp.head(20), use_container_width=True, hide_index=True)

    if st.button("Import (append)", type="primary"):
        required = {"company","role","status"}
        missing = required - set(imp.columns)
        if missing:
            st.error(f"Missing required columns: {', '.join(sorted(missing))}")
            st.stop()

        count = 0
        for _, r in imp.iterrows():
            payload = {
                "company": str(r.get("company","")).strip(),
                "role": str(r.get("role","")).strip(),
                "status": str(r.get("status","Interested")).strip() or "Interested",
                "location": str(r.get("location","")).strip(),
                "link": str(r.get("link","")).strip(),
                "channel": str(r.get("channel","")).strip(),
                "cv_version": str(r.get("cv_version","Custom")).strip(),
                "tags": str(r.get("tags","")).strip(),
                "contact_name": str(r.get("contact_name","")).strip(),
                "contact_email": str(r.get("contact_email","")).strip(),
                "salary_min": None if pd.isna(r.get("salary_min")) else int(r.get("salary_min")),
                "salary_max": None if pd.isna(r.get("salary_max")) else int(r.get("salary_max")),
                "date_interested": str(r.get("date_interested","")).strip(),
                "date_applied": str(r.get("date_applied","")).strip(),
                "date_outcome": str(r.get("date_outcome","")).strip(),
                "next_followup": str(r.get("next_followup","")).strip(),
                "jd_text": str(r.get("jd_text","")).strip(),
                "notes": str(r.get("notes","")).strip(),
            }
            if not payload["company"] or not payload["role"]:
                continue
            upsert_job(conn, None, payload)
            count += 1

        st.success(f"Imported {count} rows.")

st.divider()
st.subheader("Backup / Restore DB")

backup_dir = os.path.join("jobtracker", "backups")
os.makedirs(backup_dir, exist_ok=True)

if st.button("Create DB backup", type="primary"):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(backup_dir, f"jobs_{stamp}.db")
    shutil.copyfile(DB_PATH, out)
    st.success(f"Backup created: {out}")

st.write("Restore from a DB file (replaces current DB):")
db_up = st.file_uploader("Upload a .db backup", type=["db"])
if db_up and st.button("Restore DB (replace current)", type="secondary"):
    # Save uploaded db to a temp then replace
    tmp_path = os.path.join(backup_dir, "_restore_tmp.db")
    with open(tmp_path, "wb") as f:
        f.write(db_up.getbuffer())
    shutil.copyfile(tmp_path, DB_PATH)
    st.warning("DB restored. Restart the app.")
