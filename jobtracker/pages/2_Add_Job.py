import re
import streamlit as st
import pandas as pd
from datetime import date, timedelta

from lib.db import (
    get_conn, init_db, upsert_job, fetch_jobs,
    STATUS_ORDER, CHANNELS, CV_VERSIONS, infer_channel, parse_tags
)

st.set_page_config(page_title="Add Job", layout="wide")
st.title("Add Job (smart)")
st.caption("Paste link + JD. It fills the obvious stuff so you can move on with your life.")

conn = get_conn()
init_db(conn)

def normalize_url(u: str) -> str:
    u = (u or "").strip()
    if not u:
        return ""
    if u.startswith("http://") or u.startswith("https://"):
        return u
    return "https://" + u

def suggest_from_link(url: str):
    """
    Best-effort parsing from LinkedIn-like URLs.
    Returns (company_guess, role_guess)
    """
    u = (url or "").strip()
    if not u:
        return ("", "")
    u_low = u.lower()

    # LinkedIn job URLs sometimes include title-ish fragments; this is best-effort only.
    # Example patterns: /jobs/view/<id>/
    # We can't fetch the page, so we just try to parse readable slugs if present.
    role_guess = ""
    company_guess = ""

    m = re.search(r"/company/([^/?#]+)", u_low)
    if m:
        company_guess = m.group(1).replace("-", " ").title()

    m2 = re.search(r"/jobs/view/([^/?#]+)", u_low)
    if m2:
        frag = m2.group(1)
        # if it's numeric, ignore
        if not frag.isdigit():
            role_guess = frag.replace("-", " ").title()

    return (company_guess, role_guess)

def auto_tags_from_jd(jd: str, k: int = 10):
    jd = (jd or "").lower()
    jd = re.sub(r"[^a-z0-9+\s#./-]", " ", jd)
    toks = [t.strip() for t in jd.split() if t.strip()]
    stop = set("""
a an and are as at be by for from has have if in into is it its of on or that the their there these this to was were will with you your
""".split())
    toks = [t for t in toks if t not in stop and len(t) > 2 and not t.isdigit()]

    # count
    from collections import Counter
    c = Counter(toks)
    # prefer tech-ish tokens too
    picks = []
    for w, _ in c.most_common(200):
        if w in ("sql","python","powerbi","tableau","excel","streamlit","etl","api","aws","gcp","azure","marketing","tiktok","meta","youtube","ga4","seo","sem","crm","fraud","risk","ml","ai"):
            picks.append(w)
        elif len(picks) < k:
            picks.append(w)
        if len(picks) >= k:
            break
    # normalize capitalization for tags
    nice = []
    for w in picks[:k]:
        if w in ("sql","etl","api","aws","gcp","ml","ai","seo","sem","crm"):
            nice.append(w.upper() if w in ("sql","etl","api","ml","ai","crm","seo","sem") else w.upper())
        elif w == "powerbi":
            nice.append("Power BI")
        else:
            nice.append(w.title() if len(w) > 3 else w.upper())
    return ", ".join(dict.fromkeys(nice))

# --- Inputs ---
c1, c2, c3 = st.columns([1.2, 1.2, 0.8])

with c1:
    company = st.text_input("Company *", value="")
    role = st.text_input("Role *", value="")
with c2:
    link = st.text_input("Link", value="")
    location = st.text_input("Location", value="")
with c3:
    cv_version = st.selectbox("CV version", CV_VERSIONS, index=0)
    status = st.selectbox("Status", STATUS_ORDER, index=0)

# Smart helpers row
h1, h2, h3, h4 = st.columns([1,1,1,1])
with h1:
    if st.button("Guess from link"):
        c_guess, r_guess = suggest_from_link(link)
        if not company and c_guess:
            company = c_guess
            st.session_state["company_fill"] = company
        if not role and r_guess:
            role = r_guess
            st.session_state["role_fill"] = role
        st.info("Best-effort guess applied (if anything was guessable).")
with h2:
    if st.button("Auto channel"):
        st.session_state["channel_fill"] = infer_channel(link)
        st.info("Channel set from link.")
with h3:
    quick_follow = st.selectbox("Next follow-up", ["(none)", "+3 days", "+7 days", "+14 days"], index=1)
with h4:
    channel = st.selectbox("Channel", CHANNELS, index=0)

# Apply fills if any
if "channel_fill" in st.session_state:
    try:
        channel = st.session_state["channel_fill"]
    except Exception:
        pass

if "company_fill" in st.session_state and not company:
    company = st.session_state["company_fill"]
if "role_fill" in st.session_state and not role:
    role = st.session_state["role_fill"]

st.text_input("Company * (active)", value=company, key="company_active", disabled=True)
st.text_input("Role * (active)", value=role, key="role_active", disabled=True)

tags = st.text_input("Tags (comma-separated)", value="")
contact_name = st.text_input("Contact name", value="")
contact_email = st.text_input("Contact email", value="")

s1, s2 = st.columns(2)
with s1:
    salary_min = st.text_input("Salary min (optional)", value="")
with s2:
    salary_max = st.text_input("Salary max (optional)", value="")

jd_text = st.text_area("Job description (paste)", height=220, value="")

b1, b2, b3 = st.columns([1,1,1])
with b1:
    if st.button("Suggest tags from JD"):
        if jd_text.strip():
            tags = auto_tags_from_jd(jd_text, k=12)
            st.session_state["tags_fill"] = tags
            st.info("Suggested tags inserted.")
        else:
            st.warning("Paste JD first.")
with b2:
    save = st.button("Save job", type="primary")
with b3:
    save_add = st.button("Save + add another")

# apply tags fill if used
if "tags_fill" in st.session_state and not tags:
    tags = st.session_state["tags_fill"]

# Follow-up date compute
next_followup = ""
if quick_follow != "(none)":
    days = int(quick_follow.replace("+","").replace(" days","").strip())
    next_followup = (date.today() + timedelta(days=days)).isoformat()

def to_int_or_none(x):
    x = (x or "").strip()
    if not x:
        return None
    x = re.sub(r"[^\d]", "", x)
    return int(x) if x else None

if save or save_add:
    company2 = (company or "").strip()
    role2 = (role or "").strip()
    if not company2 or not role2:
        st.error("Company and Role are required. Don’t be lazy.")
        st.stop()

    payload = {
        "company": company2,
        "role": role2,
        "location": (location or "").strip(),
        "link": normalize_url(link),
        "channel": channel or infer_channel(link),
        "status": status,
        "cv_version": cv_version,
        "tags": parse_tags(tags),
        "contact_name": (contact_name or "").strip(),
        "contact_email": (contact_email or "").strip(),
        "salary_min": to_int_or_none(salary_min),
        "salary_max": to_int_or_none(salary_max),
        "date_interested": date.today().isoformat() if status == "Interested" else "",
        "date_applied": date.today().isoformat() if status in ("Applied","Interview","Offer","Rejected","Ghosted") else "",
        "date_outcome": date.today().isoformat() if status in ("Interview","Offer","Rejected","Ghosted") else "",
        "next_followup": next_followup,
        "jd_text": jd_text.strip(),
        "notes": ""
    }

    upsert_job(conn, None, payload)
    st.success("Saved.")

    if save_add:
        # Clear most fields but keep CV version and status as-is
        st.session_state.pop("company_fill", None)
        st.session_state.pop("role_fill", None)
        st.session_state.pop("tags_fill", None)
        st.rerun()

st.divider()
st.subheader("Recent jobs (sanity check)")
df = fetch_jobs(conn)
if df is not None and not df.empty:
    show = df[["id","company","role","status","channel","cv_version","next_followup"]].head(10).copy()
    if "next_followup" in show.columns:
        show["next_followup"] = show["next_followup"].dt.date.astype(str).replace("NaT","")
    st.dataframe(show, use_container_width=True, hide_index=True)
