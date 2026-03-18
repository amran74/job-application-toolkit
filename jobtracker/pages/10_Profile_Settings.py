import streamlit as st
from lib.db import get_conn, init_db, set_setting, get_setting

st.set_page_config(page_title="Profile Settings", layout="wide")
st.title("Profile Settings")

conn = get_conn()
init_db(conn)

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

if st.button("Save profile", type="primary"):
    set_setting(conn, "profile_name", name.strip())
    set_setting(conn, "profile_headline", headline.strip())
    set_setting(conn, "profile_email", email.strip())
    set_setting(conn, "profile_phone", phone.strip())
    set_setting(conn, "profile_github_url", github_url.strip())
    set_setting(conn, "profile_linkedin_url", linkedin_url.strip())
    set_setting(conn, "profile_website_url", website_url.strip())
    set_setting(conn, "profile_location", location.strip())
    st.success("Saved.")
