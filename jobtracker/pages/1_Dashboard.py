import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
from lib.db import get_conn, init_db, fetch_jobs, STATUS_ORDER, CHANNELS, CV_VERSIONS, metrics, update_status

st.set_page_config(page_title="Dashboard", layout="wide")

conn = get_conn()
init_db(conn)
df = fetch_jobs(conn)

st.title("Dashboard")
m = metrics(df)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total applied", m["total_applied"])
c2.metric("App → Interview/Offer", f'{m["app_to_interview"]:.1f}%')
c3.metric("Interview → Offer", f'{m["interview_to_offer"]:.1f}%')
c4.metric("Ghost rate", f'{m["ghost_rate"]:.1f}%')
c5.metric("Avg days to outcome", "-" if m["avg_days_to_outcome"] is None else f'{m["avg_days_to_outcome"]:.1f}')

if df.empty:
    st.info("No jobs yet. Go to Add Job.")
    st.stop()

# Filters
f1, f2, f3, f4 = st.columns([2,2,2,2])
with f1:
    f_status = st.multiselect("Status", STATUS_ORDER, default=STATUS_ORDER)
with f2:
    f_channel = st.multiselect("Channel", CHANNELS, default=CHANNELS)
with f3:
    f_cv = st.multiselect("CV version", CV_VERSIONS, default=CV_VERSIONS)
with f4:
    q = st.text_input("Search", value="")

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

# Follow-up reminders
today = pd.Timestamp(date.today())
rem = view[(view["next_followup"].notna()) & (view["next_followup"] <= today) & (view["status"].isin(["Applied","Interview"]))].copy()
st.subheader("Follow-ups due")
if rem.empty:
    st.write("None due. Either you're on top of things, or you forgot to set follow-ups.")
else:
    st.dataframe(rem[["id","company","role","status","next_followup","contact_email","channel"]], use_container_width=True, hide_index=True)

st.subheader("Jobs table")
cols = ["id","company","role","location","channel","cv_version","status","date_applied","next_followup","tags","link"]
st.dataframe(view[cols], use_container_width=True, hide_index=True)

st.subheader("One-click status update")
choices = [f'#{r.id} | {r.company} - {r.role}' for r in view.itertuples(index=False)]
pick = st.selectbox("Pick a job", choices)
job_id = int(pick.split("|")[0].strip().replace("#",""))
new_status = st.selectbox("Set status", STATUS_ORDER, index=STATUS_ORDER.index(df[df["id"]==job_id]["status"].iloc[0]))
if st.button("Update"):
    update_status(conn, job_id, new_status)
    st.success("Updated.")
    st.rerun()

# Applications over time
applied = df[df["date_applied"].notna()].copy()
if not applied.empty:
    applied["applied_day"] = applied["date_applied"].dt.date
    series = applied.groupby("applied_day").size().sort_index()
    fig = plt.figure()
    plt.plot(series.index, series.values)
    plt.xticks(rotation=45, ha="right")
    plt.title("Applications over time")
    plt.xlabel("Date")
    plt.ylabel("Count")
    st.pyplot(fig, clear_figure=True)
