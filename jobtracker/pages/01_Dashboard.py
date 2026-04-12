import streamlit as st

from lib.ui import *
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date

from lib.db import (
    get_conn, init_db, fetch_jobs,
    STATUS_ORDER, CHANNELS, CV_VERSIONS,
    metrics, update_status
)

st.set_page_config(page_title="Dashboard", layout="wide")

inject_global_css()
sidebar_brand()
conn = get_conn()
init_db(conn)
df = fetch_jobs(conn)

page_header(
    "Dashboard",
    "Monitor pipeline quality, follow-up pressure, stage conversion, and workflow health from one clean control surface.",
    eyebrow="Pipeline analytics",
)

if df.empty:
    section_title("Current state")
    soft_card(
        "No jobs yet",
        "There is nothing to analyze because nothing has been tracked yet. Add jobs first, then this page becomes useful instead of decorative.",
    )
    st.page_link("pages/02_Add Job.py", label="Go to Add Job")
    st.stop()

m = metrics(df)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total applied", m["total_applied"])
c2.metric("App to interview / offer", f'{m["app_to_interview"]:.1f}%')
c3.metric("Interview to offer", f'{m["interview_to_offer"]:.1f}%')
c4.metric("Ghost rate", f'{m["ghost_rate"]:.1f}%')
c5.metric("Avg days to outcome", "-" if m["avg_days_to_outcome"] is None else f'{m["avg_days_to_outcome"]:.1f}')

badge_row(["Tracked workflow", "Stage analytics", "Follow-up control", "Status maintenance"])

section_title("Filters")
f1, f2, f3, f4 = st.columns([2, 2, 2, 2])
with f1:
    f_status = st.multiselect("Status", STATUS_ORDER, default=STATUS_ORDER)
with f2:
    f_channel = st.multiselect("Channel", CHANNELS, default=CHANNELS)
with f3:
    f_cv = st.multiselect("CV version", CV_VERSIONS, default=CV_VERSIONS)
with f4:
    q = st.text_input("Search", value="", placeholder="Company, role, location, tags")

view = df[df["status"].isin(f_status)]
view = view[view["channel"].isin(f_channel)]
view = view[view["cv_version"].isin(f_cv)]

if q.strip():
    s = q.strip().lower()
    view = view[
        view["company"].fillna("").str.lower().str.contains(s) |
        view["role"].fillna("").str.lower().str.contains(s) |
        view["location"].fillna("").str.lower().str.contains(s) |
        view["tags"].fillna("").str.lower().str.contains(s)
    ]

today = pd.Timestamp(date.today())
rem = view[
    (view["next_followup"].notna()) &
    (view["next_followup"] <= today) &
    (view["status"].isin(["Applied", "Interview"]))
].copy()

left, right = st.columns([1.18, 0.82], gap="large")

with left:
    section_title("Follow-ups due")
    st.markdown('<div class="table-caption">Items already demanding action.</div>', unsafe_allow_html=True)
    if rem.empty:
        st.success("No follow-ups due.")
    else:
        rem_show = rem[["id", "company", "role", "status", "next_followup", "contact_email", "channel"]].copy()
        st.dataframe(rem_show, use_container_width=True, hide_index=True)

    section_title("Pipeline table")
    st.markdown('<div class="table-caption">Filtered workflow view for actual operational use.</div>', unsafe_allow_html=True)
    cols = ["id", "company", "role", "location", "channel", "cv_version", "status", "date_applied", "next_followup", "tags", "link"]
    existing_cols = [c for c in cols if c in view.columns]
    st.dataframe(view[existing_cols], use_container_width=True, hide_index=True)

with right:
    section_title("Fast status update")
    soft_card(
        "Keep the pipeline honest",
        "Change stage directly here so the dashboard stays useful. Weak tracking creates fake insight faster than bad code does.",
    )

    choices = [f'#{r.id} | {r.company} - {r.role}' for r in view.itertuples(index=False)]
    if choices:
        pick = st.selectbox("Pick a job", choices)
        job_id = int(pick.split("|")[0].strip().replace("#", ""))
        current_status = df[df["id"] == job_id]["status"].iloc[0]
        new_status = st.selectbox("Set status", STATUS_ORDER, index=STATUS_ORDER.index(current_status))
        if st.button("Update status", use_container_width=True):
            update_status(conn, job_id, new_status)
            st.success("Status updated.")
            st.rerun()
    else:
        st.info("No filtered jobs available for status updates.")

    section_title("Status mix")
    counts = view["status"].value_counts().reset_index()
    counts.columns = ["Status", "Count"]
    st.dataframe(counts, use_container_width=True, hide_index=True)

section_title("Applications over time")
applied = df[df["date_applied"].notna()].copy()
if applied.empty:
    st.info("No application dates recorded yet.")
else:
    applied["applied_day"] = applied["date_applied"].dt.date
    series = applied.groupby("applied_day").size().sort_index()
    fig = plt.figure(figsize=(8, 3.4))
    plt.plot(series.index, series.values)
    plt.xticks(rotation=45, ha="right")
    plt.title("Applications over time")
    plt.xlabel("Date")
    plt.ylabel("Count")
    st.pyplot(fig, clear_figure=True)
