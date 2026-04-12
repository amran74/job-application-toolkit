import streamlit as st

from lib.ui import *
from lib.db import get_conn, init_db, set_setting, get_setting

st.set_page_config(page_title="Profile Settings", layout="wide")

inject_global_css()
sidebar_brand()
conn = get_conn()
init_db(conn)

page_header(
    "Profile Settings",
    "Store reusable identity and contact details once so manual and AI-generated CV flows stay consistent across the app.",
    eyebrow="Profile and identity",
)

left, right = st.columns([1.1, 0.9], gap="large")

with right:
    section_title("Why this matters")
    soft_card(
        "Single source of truth",
        "These details feed headers, contact rows, and exported CV packages. Keep them accurate once and stop retyping the same identity block across half the product.",
    )
    soft_card(
        "Recommended use",
        "Set your name, headline, email, phone, links, and location here first. Then let the CV Builder and AI Generator reuse them everywhere else.",
    )

with left:
    section_title("Profile details")
    form_shell_open()

    def field(key, label, default=""):
        return st.text_input(label, value=get_setting(conn, key) or default)

    name = field("profile_name", "Name", "Amran")
    headline = field("profile_headline", "Default headline", "B.Sc. Information Systems | SQL | Python | Power BI")

    c1, c2 = st.columns(2)
    with c1:
        email = field("profile_email", "Email")
        phone = field("profile_phone", "Phone")
    with c2:
        github_url = field("profile_github_url", "GitHub URL")
        linkedin_url = field("profile_linkedin_url", "LinkedIn URL")

    website_url = field("profile_website_url", "Website URL")
    location = field("profile_location", "Location")

    save = st.button("Save profile", type="primary", use_container_width=True)

    form_shell_close()

if save:
    set_setting(conn, "profile_name", name.strip())
    set_setting(conn, "profile_headline", headline.strip())
    set_setting(conn, "profile_email", email.strip())
    set_setting(conn, "profile_phone", phone.strip())
    set_setting(conn, "profile_github_url", github_url.strip())
    set_setting(conn, "profile_linkedin_url", linkedin_url.strip())
    set_setting(conn, "profile_website_url", website_url.strip())
    set_setting(conn, "profile_location", location.strip())
    st.success("Profile settings saved.")
