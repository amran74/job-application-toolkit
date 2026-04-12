import os
from datetime import datetime

import streamlit as st

from lib.ui import *
from lib.pdf_export import export_cv_pdf, export_cv_pdf_he
from lib.db import get_conn, init_db, get_setting

try:
    from lib.db import fetch_cv_content_blocks
except ImportError:
    fetch_cv_content_blocks = None

st.set_page_config(page_title="CV", layout="wide")

inject_global_css()
sidebar_brand()
st.title("CV (Manual Builder)")
st.caption("Reworked manual builder with saved content blocks, custom section control, bilingual export, and cleaner alignment with the new CV system.")

SECTION_SPECS = [
    ("summary", "Summary"),
    ("experience", "Experience"),
    ("projects", "Projects"),
    ("education", "Education"),
    ("skills", "Skills"),
    ("languages", "Languages"),
]

def ss_init(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

def safe_text(value):
    return str(value or "").strip()

def normalize_url(u: str) -> str:
    u = safe_text(u)
    if not u:
        return ""
    if u.startswith("http://") or u.startswith("https://"):
        return u
    return "https://" + u

def get_language_label(code: str) -> str:
    return {"en": "English", "he": "Hebrew"}.get(code, code)

def build_block_index(df_blocks, section_key: str, language_code: str):
    out = {}
    if df_blocks is None or getattr(df_blocks, "empty", True):
        return out

    sub = df_blocks.copy()
    sub = sub[
        sub["section_key"].astype(str).str.lower().eq(section_key) &
        sub["language_code"].astype(str).str.lower().eq(language_code)
    ].copy()

    if "is_active" in sub.columns:
        sub = sub[sub["is_active"].fillna(0).astype(int).eq(1)]

    if sub.empty:
        return out

    sort_cols = [c for c in ["sort_order", "title", "id"] if c in sub.columns]
    if sort_cols:
        sub = sub.sort_values(sort_cols)

    for row in sub.itertuples(index=False):
        label = f"#{int(row.id)} | {safe_text(row.title)}"
        out[label] = {
            "id": int(row.id),
            "title": safe_text(row.title),
            "content": safe_text(row.content),
        }
    return out

def combine_section_text(mode: str, selected_labels, option_map: dict, custom_text: str) -> str:
    parts = []

    if mode in ("Saved blocks only", "Saved blocks + custom"):
        for label in selected_labels:
            item = option_map.get(label)
            if item and safe_text(item.get("content")):
                parts.append(safe_text(item["content"]))

    if mode in ("Custom only", "Saved blocks + custom"):
        if safe_text(custom_text):
            parts.append(safe_text(custom_text))

    return "\n\n".join([x for x in parts if safe_text(x)]).strip()

def build_export_filename(language_code: str, name: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join([c for c in safe_text(name) if c.isalnum() or c in ("_", "-")]).strip()
    if not safe_name:
        safe_name = "cv"
    return f"{safe_name}_{language_code}_{ts}.pdf"

# Load settings / profile
conn = get_conn()
init_db(conn)

profile = {
    "name": get_setting(conn, "profile_name") or "Amran",
    "headline": get_setting(conn, "profile_headline") or "",
    "email": get_setting(conn, "profile_email") or "",
    "phone": get_setting(conn, "profile_phone") or "",
    "github_url": get_setting(conn, "profile_github_url") or "",
    "linkedin_url": get_setting(conn, "profile_linkedin_url") or "",
    "website_url": get_setting(conn, "profile_website_url") or "",
    "location": get_setting(conn, "profile_location") or "",
}

blocks_df = None
blocks_available = callable(fetch_cv_content_blocks)
if blocks_available:
    try:
        blocks_df = fetch_cv_content_blocks(conn, active_only=True)
    except Exception as e:
        blocks_available = False
        st.warning(f"Saved content blocks are unavailable right now: {e}")

use_profile = st.toggle("Use Profile defaults", value=True)
output_language = st.selectbox("Output language", options=["en", "he"], format_func=get_language_label, index=0)

# Header
st.subheader("Header")
c1, c2, c3 = st.columns(3)

with c1:
    name = st.text_input("Name", value=(profile["name"] if use_profile else "Amran"))
    headline = st.text_input("Headline", value=(profile["headline"] if use_profile else ""))

with c2:
    email = st.text_input("Email", value=(profile["email"] if use_profile else ""))
    phone = st.text_input("Phone", value=(profile["phone"] if use_profile else ""))

with c3:
    github_url = st.text_input("GitHub URL", value=(profile["github_url"] if use_profile else ""))
    linkedin_url = st.text_input("LinkedIn URL", value=(profile["linkedin_url"] if use_profile else ""))

website_url = st.text_input("Website URL", value=(profile["website_url"] if use_profile else ""))
location = st.text_input("Location", value=(profile["location"] if use_profile else ""))

contacts = {
    "email": safe_text(email),
    "phone": safe_text(phone),
    "github_url": normalize_url(github_url),
    "linkedin_url": normalize_url(linkedin_url),
    "website_url": normalize_url(website_url),
    "location": safe_text(location),
}

st.divider()
st.subheader("Section builder")

assembled = {}

for section_key, section_label in SECTION_SPECS:
    ss_init(f"manual_mode_{section_key}", "Saved blocks + custom" if section_key != "summary" else "Custom only")
    ss_init(f"manual_custom_{section_key}", "")
    ss_init(f"manual_selected_{output_language}_{section_key}", [])

    with st.expander(section_label, expanded=(section_key in ["summary", "experience", "projects"])):
        mode = st.selectbox(
            f"{section_label} source",
            options=["Custom only", "Saved blocks only", "Saved blocks + custom"],
            index=["Custom only", "Saved blocks only", "Saved blocks + custom"].index(st.session_state[f"manual_mode_{section_key}"]),
            key=f"manual_mode_widget_{section_key}",
        )
        st.session_state[f"manual_mode_{section_key}"] = mode

        option_map = build_block_index(blocks_df, section_key, output_language) if blocks_available else {}

        selected_labels = []
        if mode in ("Saved blocks only", "Saved blocks + custom"):
            selected_labels = st.multiselect(
                f"Saved {section_label} blocks ({get_language_label(output_language)})",
                options=list(option_map.keys()),
                default=st.session_state.get(f"manual_selected_{output_language}_{section_key}", []),
                key=f"manual_selected_widget_{output_language}_{section_key}",
            )
            st.session_state[f"manual_selected_{output_language}_{section_key}"] = selected_labels

            if not option_map:
                st.info(f"No saved {section_label.lower()} blocks found for {get_language_label(output_language)}.")

        custom_text = ""
        if mode in ("Custom only", "Saved blocks + custom"):
            height = 140
            if section_key in ("experience", "projects"):
                height = 220
            elif section_key == "summary":
                height = 120

            placeholder_map = {
                "summary": "Write a short professional summary...",
                "experience": "Example:\nSuper-Pharm, Kiryat Ata - Shift Manager | 2022-Present\n- Led shifts and improved operations\n- Managed customer-facing workflow",
                "projects": "Example:\nAI CV & Job Application Toolkit | Python, Streamlit, OpenAI API | 2026\n- Built a tool that tailors CVs to job descriptions\n- GitHub: https://github.com/...",
                "education": "Example:\nB.Sc. - Information Systems\nUniversity Name, Location\n2022-2026",
                "skills": "Example:\nProgramming: Python, SQL\nBI: Power BI, Excel\nTools: Streamlit, Git",
                "languages": "Example:\nArabic: Native\nEnglish: Fluent\nHebrew: Fluent",
            }

            custom_text = st.text_area(
                f"Custom {section_label}",
                value=st.session_state.get(f"manual_custom_{section_key}", ""),
                height=height,
                placeholder=placeholder_map.get(section_key, ""),
                key=f"manual_custom_widget_{section_key}",
            )
            st.session_state[f"manual_custom_{section_key}"] = custom_text

        assembled_text = combine_section_text(mode, selected_labels, option_map, custom_text)
        assembled[section_key] = assembled_text

        if safe_text(assembled_text):
            st.markdown("**Preview**")
            st.code(assembled_text, language=None)

st.divider()
st.subheader("Export")

default_filename = build_export_filename(output_language, name)
filename = st.text_input("Output filename", value=default_filename)

summary_text = assembled.get("summary", "")
experience_text = assembled.get("experience", "")
projects_text = assembled.get("projects", "")
education_text = assembled.get("education", "")
skills_text = assembled.get("skills", "")
languages_text = assembled.get("languages", "")

sections = [
    ("Experience" if output_language == "en" else "ניסיון", experience_text, "bullets"),
    ("Projects" if output_language == "en" else "פרויקטים", projects_text, "bullets_links"),
    ("Skills" if output_language == "en" else "כישורים", skills_text, "text"),
    ("Education" if output_language == "en" else "השכלה", education_text, "text"),
    ("Languages" if output_language == "en" else "שפות", languages_text, "text"),
]

non_empty_sections = [x for x in sections if safe_text(x[1])]

export_dir = os.path.join("jobtracker", "exports", "manual")
os.makedirs(export_dir, exist_ok=True)
output_path = os.path.join(export_dir, filename)

if st.button("Export CV PDF", type="primary", use_container_width=True):
    if not safe_text(name):
        st.error("Name is required.")
    elif not safe_text(summary_text) and not non_empty_sections:
        st.error("Add at least one section or summary before exporting.")
    else:
        try:
            if output_language == "he":
                export_cv_pdf_he(
                    path=output_path,
                    name=name,
                    headline=headline,
                    contacts=contacts,
                    summary=summary_text,
                    sections=non_empty_sections,
                )
            else:
                export_cv_pdf(
                    path=output_path,
                    name=name,
                    headline=headline,
                    contacts=contacts,
                    summary=summary_text,
                    sections=non_empty_sections,
                )

            st.success(f"Exported PDF to {output_path}")

            with open(output_path, "rb") as f:
                st.download_button(
                    "Download CV PDF",
                    f,
                    file_name=os.path.basename(output_path),
                    mime="application/pdf",
                    use_container_width=True,
                )
        except Exception as e:
            st.error(f"Export failed: {e}")

st.caption("This builder now works with the new saved block system. Use saved blocks, custom text, or both for each section.")
