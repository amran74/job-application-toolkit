import streamlit as st
import sqlite3
from lib.db import DB_PATH, get_conn, init_db, fetch_jobs, delete_job

st.set_page_config(page_title="Settings", layout="wide")

st.title("Settings / Backup")

st.subheader("Backup DB")
st.caption("This is the real value. If you lose your DB, your tracking system becomes a motivational story.")

if st.button("Create backup"):
    import shutil, time
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = f"jobs_backup_{stamp}.db"
    shutil.copy(DB_PATH, backup)
    st.success(f"Created {backup}")

st.subheader("Danger zone")
conn = get_conn()
init_db(conn)
df = fetch_jobs(conn)

if df.empty:
    st.info("Nothing to delete.")
else:
    pick = st.selectbox("Delete a job", [f'#{r.id} | {r.company} - {r.role}' for r in df.itertuples(index=False)])
    if st.button("Delete selected"):
        job_id = int(pick.split("|")[0].strip().replace("#",""))
        delete_job(conn, job_id)
        st.warning("Deleted.")
        st.rerun()
