import streamlit as st

from lib.ui import *
import pandas as pd
from datetime import date

from lib.db import get_conn, init_db, fetch_jobs

st.set_page_config(page_title="Job Application Toolkit", layout="wide")

inject_global_css()
sidebar_brand()
conn = get_conn()
init_db(conn)
df = fetch_jobs(conn)

page_header(
    "Job Application Toolkit",
    "A structured workspace for job tracking, reusable CV content, bilingual AI generation, and versioned application output.",
    eyebrow="Application workflow system",
)

if df is None or df.empty:
    left, right = st.columns([1.15, 0.85], gap="large")

    with left:
        section_title("Start here")
        soft_card(
            "No jobs yet",
            "Add the first tracked role, save the baseline CV, and build reusable content blocks. The app is meant to operate like a system, not sit here looking theoretical.",
        )
        badge_row(["Job tracking", "AI CV generation", "Bilingual output", "Version history"])

    with right:
        section_title("Core setup")
        quick_link_card("Add Job", "Create the first tracked opportunity.")
        st.page_link("pages/02_Add Job.py", label="Open Add Job")

        quick_link_card("Baseline CV", "Store the source material used for AI tailoring.")
        st.page_link("pages/08_Baseline CV.py", label="Open Baseline CV")

        quick_link_card("Profile Settings", "Set name, email, links, and headline once.")
        st.page_link("pages/09_Profile Settings.py", label="Open Profile Settings")

        quick_link_card("Content Blocks", "Save reusable projects, experience, skills, and education.")
        st.page_link("pages/05_CV Content Blocks.py", label="Open Content Blocks")

    st.stop()

today = pd.to_datetime(date.today())
df2 = df.copy()

for col in ["next_followup", "created_at"]:
    if col in df2.columns:
        df2[col] = pd.to_datetime(df2[col], errors="coerce")

total = len(df2)
applied_plus = int(df2["status"].isin(["Applied", "Interview", "Offer", "Rejected", "Ghosted"]).sum())
interviews = int(df2["status"].eq("Interview").sum())
offers = int(df2["status"].eq("Offer").sum())
interview_rate = (interviews / applied_plus * 100) if applied_plus else 0

fu_due = df2[df2["next_followup"].notna() & (df2["next_followup"] <= today)].copy()
stale = df2[
    (df2["status"] == "Interested")
    & df2["created_at"].notna()
    & (df2["created_at"] <= (today - pd.to_timedelta(7, unit="D")))
].copy()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Tracked jobs", total)
m2.metric("Applied+", applied_plus)
m3.metric("Interviews", interviews)
m4.metric("Interview rate", f"{interview_rate:.1f}%")

left, right = st.columns([1.2, 0.8], gap="large")

with left:
    section_title("Operational focus")
    soft_card(
        "What deserves attention",
        "Handle overdue follow-ups first, clear stale interest second, and generate tailored CV output only after the workflow data is honest.",
    )

    section_title("Due follow-ups")
    st.markdown('<div class="table-caption">Applications that already need action.</div>', unsafe_allow_html=True)
    if fu_due.empty:
        st.success("No follow-ups due today.")
    else:
        show = fu_due.sort_values("next_followup")[["id", "company", "role", "status", "next_followup"]].copy()
        show["next_followup"] = show["next_followup"].dt.date.astype(str)
        st.dataframe(show, use_container_width=True, hide_index=True)

    section_title("Stale interested jobs")
    st.markdown('<div class="table-caption">Old interest with no movement is usually hesitation, noise, or both.</div>', unsafe_allow_html=True)
    if stale.empty:
        st.success("No stale interested jobs.")
    else:
        show2 = stale.sort_values("created_at")[["id", "company", "role", "created_at"]].copy()
        show2["created_at"] = show2["created_at"].dt.date.astype(str)
        st.dataframe(show2, use_container_width=True, hide_index=True)

with right:
    section_title("Core workflow")
    quick_link_card("AI CV Generator", "Generate tailored English and Hebrew CV output with cover support.")
    st.page_link("pages/03_AI CV Generator.py", label="Open AI CV Generator")

    quick_link_card("Manual CV Builder", "Assemble a CV from saved blocks, custom sections, or both.")
    st.page_link("pages/04_Manual CV Builder.py", label="Open Manual CV Builder")

    quick_link_card("Content Blocks", "Manage reusable projects, experience, skills, and languages.")
    st.page_link("pages/05_CV Content Blocks.py", label="Open Content Blocks")

    quick_link_card("AI Content Assistant", "Turn messy text into structured reusable content blocks.")
    st.page_link("pages/06_AI Content Assistant.py", label="Open AI Content Assistant")
