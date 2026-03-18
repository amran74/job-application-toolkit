import streamlit as st
import pandas as pd
from datetime import date, timedelta
from lib.db import get_conn, init_db, fetch_jobs

st.set_page_config(page_title="Daily Focus", layout="wide")
st.title("Daily Focus")
st.caption("Your job hunt, reduced to a to-do list. Humans love avoiding decisions, so here you go.")

conn = get_conn()
init_db(conn)
df = fetch_jobs(conn)

if df is None or df.empty:
    st.info("No jobs yet. Add jobs first, then come back.")
    st.stop()

today = pd.to_datetime(date.today())
df2 = df.copy()

# Ensure dates are datetime
for col in ["next_followup", "created_at", "date_interested", "date_applied", "last_update"]:
    if col in df2.columns:
        df2[col] = pd.to_datetime(df2[col], errors="coerce")

# Follow-ups due
fu = df2[df2["next_followup"].notna()].copy()
fu_due = fu[fu["next_followup"] <= today].sort_values("next_followup")

# Stale interested jobs (interested but not applied within 7 days)
stale_days = st.slider("Consider 'Interested' stale after days", 3, 21, 7)
stale_cutoff = today - pd.to_timedelta(stale_days, unit="D")
stale = df2[(df2["status"] == "Interested") & (df2["created_at"].notna()) & (df2["created_at"] <= stale_cutoff)].copy()
stale = stale.sort_values("created_at")

# Metrics-ish
col1, col2, col3 = st.columns(3)
col1.metric("Follow-ups due", int(len(fu_due)))
col2.metric("Stale 'Interested'", int(len(stale)))
col3.metric("Total jobs", int(len(df2)))

st.divider()

st.subheader("1) Follow-ups due (today or overdue)")
if fu_due.empty:
    st.success("None due. Either you're disciplined or you forgot to set follow-ups.")
else:
    show = fu_due[["id","company","role","status","next_followup","channel","link"]].copy()
    show["next_followup"] = show["next_followup"].dt.date.astype(str)
    st.dataframe(show, use_container_width=True, hide_index=True)
    st.info("Go to Quick Actions → select job → 'I followed up today'.")

st.divider()

st.subheader(f"2) Stale 'Interested' jobs (older than {stale_days} days)")
if stale.empty:
    st.success("No stale jobs. You’re either applying or rejecting fast. Good.")
else:
    show2 = stale[["id","company","role","status","created_at","channel","link"]].copy()
    show2["created_at"] = show2["created_at"].dt.date.astype(str)
    st.dataframe(show2, use_container_width=True, hide_index=True)
    st.info("Decision rule: if it’s still 'Interested' after a week, either apply today or delete it. No limbo.")

st.divider()

st.subheader("3) Today’s simple plan (no excuses)")
st.write("• Do all follow-ups due (max 15 minutes).")
st.write("• Apply to 1–3 from stale list (or delete them).")
st.write("• Add 1 new job if you have none queued.")

