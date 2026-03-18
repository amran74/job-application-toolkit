import streamlit as st
import pandas as pd
from datetime import date
from lib.db import get_conn, init_db, fetch_jobs

st.set_page_config(page_title="Job Tracker", layout="wide")
st.title("Job Tracker")
st.caption("Not a motivational poster. A control panel.")

conn = get_conn()
init_db(conn)
df = fetch_jobs(conn)

if df is None or df.empty:
    st.info("No jobs yet. Start with Add Job. Then this page becomes useful.")
    st.stop()

today = pd.to_datetime(date.today())

# normalize dates
df2 = df.copy()
for col in ["next_followup", "created_at", "date_interested", "date_applied", "date_outcome", "last_update"]:
    if col in df2.columns:
        df2[col] = pd.to_datetime(df2[col], errors="coerce")

# KPIs
total = len(df2)
applied = int(df2["status"].isin(["Applied","Interview","Offer","Rejected","Ghosted"]).sum())
interviews = int(df2["status"].eq("Interview").sum())
offers = int(df2["status"].eq("Offer").sum())
ghosted = int(df2["status"].eq("Ghosted").sum())
interview_rate = (interviews / applied * 100) if applied else 0

fu_due = df2[df2["next_followup"].notna() & (df2["next_followup"] <= today)].copy()
stale = df2[(df2["status"] == "Interested") & df2["created_at"].notna() & (df2["created_at"] <= (today - pd.to_timedelta(7, unit="D")))].copy()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total jobs", total)
c2.metric("Applied+", applied)
c3.metric("Interviews", interviews)
c4.metric("Offers", offers)
c5.metric("Interview rate", f"{interview_rate:.1f}%")

st.divider()

left, right = st.columns([1.1, 0.9])

with left:
    st.subheader("Today")
    if fu_due.empty:
        st.success("No follow-ups due today.")
    else:
        st.warning(f"{len(fu_due)} follow-up(s) due. Do them first, then pretend you’re busy.")
        show = fu_due.sort_values("next_followup")[["id","company","role","status","next_followup"]].copy()
        show["next_followup"] = show["next_followup"].dt.date.astype(str)
        st.dataframe(show, use_container_width=True, hide_index=True)

    st.subheader("Stale 'Interested' (older than 7 days)")
    if stale.empty:
        st.success("None stale. Nice.")
    else:
        st.info("These are sitting in limbo. Apply or delete. Limbo is cowardice.")
        show2 = stale.sort_values("created_at")[["id","company","role","created_at"]].copy()
        show2["created_at"] = show2["created_at"].dt.date.astype(str)
        st.dataframe(show2, use_container_width=True, hide_index=True)

with right:
    st.subheader("Quick actions")
    st.page_link("pages/2_Add_Job.py", label="Add a Job", icon="➕")
    st.page_link("pages/1_Dashboard.py", label="Dashboard", icon="📊")
    st.page_link("pages/11_Quick_Actions.py", label="Quick Actions (follow-ups)", icon="✅")
    st.page_link("pages/5_CV.py", label="Manual CV", icon="🧾")
    st.page_link("pages/7_AI_CV_Generator.py", label="AI CV Generator", icon="🤖")
    st.page_link("pages/9_Baseline_CV.py", label="Baseline CV", icon="📌")
    st.page_link("pages/10_Profile_Settings.py", label="Profile Settings", icon="👤")

    st.divider()
    st.subheader("Status breakdown")
    counts = df2["status"].value_counts().reset_index()
    counts.columns = ["status","count"]
    st.dataframe(counts, use_container_width=True, hide_index=True)

st.caption("If this page looks empty, it's because you haven't fed it data. Add jobs, set follow-ups, paste JDs.")
