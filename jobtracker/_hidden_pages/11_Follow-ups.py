
﻿import streamlit as st
import pandas as pd
from datetime import date
from lib.db import get_conn, init_db, fetch_jobs

st.set_page_config(page_title="Follow-ups", layout="wide")

inject_global_css()
sidebar_brand()
conn = get_conn()
init_db(conn)
df = fetch_jobs(conn)

st.title("Follow-ups")
st.caption("Templates you can copy. No auto-sending. You want reliable, not brittle.")

if df.empty:
    st.info("No jobs yet.")
    st.stop()

today = pd.Timestamp(date.today())
due = df[(df["next_followup"].notna()) & (df["next_followup"] <= today) & (df["status"].isin(["Applied","Interview"]))].copy()

st.subheader("Due now")
if due.empty:
    st.write("Nothing due.")
else:
    pick = st.selectbox("Pick one", [f'#{r.id} | {r.company} - {r.role}' for r in due.itertuples(index=False)])
    job_id = int(pick.split("|")[0].strip().replace("#",""))
    job = df[df["id"] == job_id].iloc[0]

    name = (job.get("contact_name") or "").strip()
    company = job["company"]
    role = job["role"]
    channel = job.get("channel") or "application"
    when = job["date_applied"].date().isoformat() if pd.notna(job["date_applied"]) else "recently"

    subject = f"Following up: {role} at {company}"

    body = f"""Hi {name + ' ' if name else ''}I hope you're doing well.

I wanted to follow up on my {channel} for the {role} position at {company} submitted on {when}.
I'm still very interested, and I’d be happy to share any additional information or jump on a quick call if helpful.

Thanks,
Amran
"""
    st.text_input("Subject", value=subject)
    st.text_area("Email", value=body, height=220)

st.subheader("Not due yet (upcoming)")
up = df[(df["next_followup"].notna()) & (df["next_followup"] > today) & (df["status"].isin(["Applied","Interview"]))].copy()
if up.empty:
    st.write("No upcoming follow-ups set.")
else:
    st.dataframe(up[["id","company","role","status","next_followup","contact_email"]], use_container_width=True, hide_index=True)
