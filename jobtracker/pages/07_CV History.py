import os
import json
import streamlit as st

from lib.ui import *
from lib.db import get_conn, init_db, fetch_jobs, fetch_cv_versions, read_cv_version

st.set_page_config(page_title="CV History", layout="wide")

inject_global_css()
sidebar_brand()
st.title("CV History (per job)")
st.caption("Browse saved CV/cover versions per job and download the PDFs you generated.")

conn = get_conn()
init_db(conn)
df = fetch_jobs(conn)

if df.empty:
    st.info("No jobs found.")
    st.stop()

choices = [f'#{r.id} | {r.company} - {r.role}' for r in df.itertuples(index=False)]
pick = st.selectbox("Select job", choices)
job_id = int(pick.split("|")[0].strip().replace("#",""))

versions = fetch_cv_versions(conn, job_id)
if versions.empty:
    st.info("No CV versions saved for this job yet. Use 'AI CV Generator' first.")
    st.stop()

st.subheader("Saved versions")
st.dataframe(versions, use_container_width=True, hide_index=True)

v_choices = [f'v#{r.id} | {r.created_at} | {r.archetype} | {r.tone}' for r in versions.itertuples(index=False)]
v_pick = st.selectbox("Open a version", v_choices)
version_id = int(v_pick.split("|")[0].strip().replace("v#",""))

record = read_cv_version(conn, version_id)
if not record:
    st.error("Version not found.")
    st.stop()

cv = json.loads(record["cv_json"])
cover = json.loads(record["cover_json"])
notes = json.loads(record["notes_json"])

st.subheader("Preview")
st.markdown("**Headline**"); st.write(cv.get("headline",""))
st.markdown("**Summary**"); st.write(cv.get("summary",""))
st.markdown("**Experience**"); st.write(cv.get("experience",""))
st.markdown("**Skills**"); st.write(cv.get("skills",""))
st.markdown("**Education**"); st.write(cv.get("education",""))
st.markdown("**Projects**"); st.write(cv.get("projects",""))

st.subheader("Notes")
st.write("Keywords:", ", ".join(notes.get("keywords_used", [])) or "-")
for w in notes.get("warnings", [])[:20]:
    st.write(f"- {w}")

st.subheader("Files")
cv_path = record.get("cv_pdf_path")
cl_path = record.get("cover_pdf_path")

col1, col2 = st.columns(2)
with col1:
    if cv_path and os.path.exists(cv_path):
        with open(cv_path, "rb") as f:
            st.download_button("Download CV PDF", f, file_name=os.path.basename(cv_path), mime="application/pdf")
    else:
        st.write("No CV PDF saved for this version yet.")
with col2:
    if cl_path and os.path.exists(cl_path):
        with open(cl_path, "rb") as f:
            st.download_button("Download Cover Letter PDF", f, file_name=os.path.basename(cl_path), mime="application/pdf")
    else:
        st.write("No cover letter PDF saved for this version yet.")
