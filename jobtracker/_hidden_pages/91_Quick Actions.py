
﻿import streamlit as st
import pandas as pd
from datetime import date, timedelta
from lib.db import get_conn, init_db, fetch_jobs, get_job, upsert_job, parse_tags

st.set_page_config(page_title="Quick Actions", layout="wide")

inject_global_css()
sidebar_brand()
st.title("Quick Actions")
st.caption("Follow-ups, duplicates, and other boring stuff that actually makes the app useful.")

conn = get_conn()
init_db(conn)
df = fetch_jobs(conn)

if df.empty:
    st.info("No jobs yet.")
    st.stop()

# --- Duplicate scan ---
st.subheader("Duplicate Detector")

tmp = df.copy()
tmp["company_norm"] = tmp["company"].fillna("").str.strip().str.lower()
tmp["role_norm"] = tmp["role"].fillna("").str.strip().str.lower()
tmp["link_norm"] = tmp["link"].fillna("").str.strip().str.lower()

dups_company_role = tmp.groupby(["company_norm","role_norm"]).size().reset_index(name="count")
dups_company_role = dups_company_role[dups_company_role["count"] > 1]

dups_link = tmp[tmp["link_norm"] != ""].groupby("link_norm").size().reset_index(name="count")
dups_link = dups_link[dups_link["count"] > 1]

if dups_company_role.empty and dups_link.empty:
    st.success("No duplicates detected. For once.")
else:
    if not dups_company_role.empty:
        st.write("Duplicates by company+role:")
        st.dataframe(dups_company_role, use_container_width=True, hide_index=True)
    if not dups_link.empty:
        st.write("Duplicates by link:")
        st.dataframe(dups_link, use_container_width=True, hide_index=True)

st.divider()

# --- Follow-up workflow ---
st.subheader("Follow-up Workflow")

choices = [f'#{r.id} | {r.company} - {r.role} | {r.status}' for r in df.itertuples(index=False)]
pick = st.selectbox("Select job", choices)
job_id = int(pick.split("|")[0].strip().replace("#",""))
job = get_job(conn, job_id) or {}

col1, col2, col3 = st.columns(3)
with col1:
    bump_days = st.number_input("Bump next follow-up (days)", min_value=1, max_value=30, value=7)
with col2:
    note = st.text_input("Optional note", value="Followed up.")
with col3:
    set_status = st.selectbox("Optional status update", ["(no change)", "Applied", "Interview", "Offer", "Rejected", "Ghosted"])

if st.button("I followed up today", type="primary"):
    today = date.today()
    next_fu = today + timedelta(days=int(bump_days))

    # append note
    old_notes = (job.get("notes") or "").strip()
    entry = f"[{today.isoformat()}] FOLLOW-UP: {note}".strip()
    new_notes = (old_notes + "\n" + entry).strip() if old_notes else entry

    payload = job.copy()
    payload["notes"] = new_notes
    payload["next_followup"] = next_fu.isoformat()

    if set_status != "(no change)":
        payload["status"] = set_status

    # Ensure required fields exist
    payload.setdefault("company","")
    payload.setdefault("role","")
    payload.setdefault("status","Interested")

    upsert_job(conn, job_id, payload)
    st.success(f"Logged follow-up. Next follow-up set to {next_fu.isoformat()}.")

if st.button("Mark as Ghosted (today)"):
    today = date.today().isoformat()
    old_notes = (job.get("notes") or "").strip()
    entry = f"[{today}] STATUS: Ghosted"
    new_notes = (old_notes + "\n" + entry).strip() if old_notes else entry

    payload = job.copy()
    payload["status"] = "Ghosted"
    payload["notes"] = new_notes
    payload.setdefault("company","")
    payload.setdefault("role","")
    upsert_job(conn, job_id, payload)
    st.warning("Marked Ghosted. Painful, but honest.")
