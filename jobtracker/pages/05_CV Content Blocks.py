import streamlit as st

from lib.ui import *
from lib.db import (
    get_conn,
    init_db,
    fetch_cv_content_blocks,
    get_cv_content_block,
    save_cv_content_block,
    delete_cv_content_block,
)

st.set_page_config(page_title="CV Content Blocks", layout="wide")

inject_global_css()
sidebar_brand()
st.title("CV Content Blocks")
st.caption("Manage reusable English and Hebrew blocks with section-specific fields for AI CV generation.")

SECTION_OPTIONS = {
    "summary": "Summary",
    "experience": "Experience",
    "projects": "Projects",
    "education": "Education",
    "skills": "Skills",
    "languages": "Languages",
}

LANGUAGE_OPTIONS = {
    "en": "English",
    "he": "Hebrew",
}

conn = get_conn()
init_db(conn)

def empty_data(section_key: str):
    if section_key == "summary":
        return {"summary": ""}
    if section_key == "projects":
        return {
            "project_name": "",
            "tools": "",
            "period": "",
            "description": "",
            "github_link": "",
            "demo_link": "",
        }
    if section_key == "experience":
        return {
            "employer": "",
            "location": "",
            "role": "",
            "start_date": "",
            "end_date": "",
            "is_current": False,
            "achievements": "",
        }
    if section_key == "education":
        return {
            "degree": "",
            "field": "",
            "institution": "",
            "location": "",
            "start_year": "",
            "end_year": "",
            "notes": "",
        }
    if section_key == "skills":
        return {
            "category": "",
            "items": "",
        }
    if section_key == "languages":
        return {
            "language": "",
            "proficiency": "",
        }
    return {}

def make_default_title(section_key: str, data: dict):
    data = data or {}

    if section_key == "summary":
        txt = str(data.get("summary", "")).strip()
        return txt[:60] if txt else "Summary"

    if section_key == "projects":
        return str(data.get("project_name", "")).strip() or "Project"

    if section_key == "experience":
        employer = str(data.get("employer", "")).strip()
        role = str(data.get("role", "")).strip()
        if employer and role:
            return f"{employer} - {role}"
        return employer or role or "Experience"

    if section_key == "education":
        degree = str(data.get("degree", "")).strip()
        institution = str(data.get("institution", "")).strip()
        if degree and institution:
            return f"{degree} - {institution}"
        return degree or institution or "Education"

    if section_key == "skills":
        category = str(data.get("category", "")).strip()
        return category or "Skills"

    if section_key == "languages":
        language = str(data.get("language", "")).strip()
        return language or "Language"

    return "Block"

df = fetch_cv_content_blocks(conn, active_only=False)

left, right = st.columns([1.2, 1.8], gap="large")

with left:
    st.subheader("Editor")

    language_code = st.selectbox(
        "Language",
        options=list(LANGUAGE_OPTIONS.keys()),
        format_func=lambda x: LANGUAGE_OPTIONS[x],
        key="editor_language",
    )

    section_key = st.selectbox(
        "Section",
        options=list(SECTION_OPTIONS.keys()),
        format_func=lambda x: SECTION_OPTIONS[x],
        key="editor_section",
    )

    df_filtered = df.copy()
    if not df_filtered.empty:
        df_filtered = df_filtered[
            df_filtered["language_code"].astype(str).str.lower().eq(language_code) &
            df_filtered["section_key"].astype(str).str.lower().eq(section_key)
        ].copy()

    option_labels = ["[New block]"]
    option_map = {}

    if not df_filtered.empty:
        df_filtered = df_filtered.sort_values(["sort_order", "updated_at", "id"], ascending=[True, False, False])
        for row in df_filtered.itertuples(index=False):
            active_mark = "" if int(row.is_active or 0) == 1 else " [inactive]"
            label = f"#{int(row.id)} | {str(row.title or '').strip()}{active_mark}"
            option_labels.append(label)
            option_map[label] = int(row.id)

    selected_label = st.selectbox("Load existing block", options=option_labels, index=0)
    selected_id = option_map.get(selected_label)
    loaded = get_cv_content_block(conn, selected_id) if selected_id else None
    data = loaded.get("data", {}) if loaded else empty_data(section_key)

    auto_title = st.toggle("Auto title from fields", value=True if not loaded else False)
    manual_title_default = loaded.get("title", "") if loaded else ""
    title = manual_title_default
    tags = loaded.get("tags", "") if loaded else ""
    sort_order = int(loaded.get("sort_order", 0)) if loaded else 0
    is_active = bool(int(loaded.get("is_active", 1))) if loaded else True

    st.markdown("#### Section fields")

    if section_key == "summary":
        data["summary"] = st.text_area("Summary", value=str(data.get("summary", "")), height=180)

    elif section_key == "projects":
        data["project_name"] = st.text_input("Project name", value=str(data.get("project_name", "")))
        data["tools"] = st.text_input("Tools / tech stack", value=str(data.get("tools", "")), placeholder="Python, Streamlit, SQLite")
        data["period"] = st.text_input("Year / period", value=str(data.get("period", "")), placeholder="2025 or 2024-2025")
        data["description"] = st.text_area("Description", value=str(data.get("description", "")), height=180)
        data["github_link"] = st.text_input("GitHub link", value=str(data.get("github_link", "")))
        data["demo_link"] = st.text_input("Demo / live link", value=str(data.get("demo_link", "")))

    elif section_key == "experience":
        data["employer"] = st.text_input("Employer", value=str(data.get("employer", "")))
        data["location"] = st.text_input("Location", value=str(data.get("location", "")))
        data["role"] = st.text_input("Role", value=str(data.get("role", "")))
        c1, c2 = st.columns(2)
        with c1:
            data["start_date"] = st.text_input("Start date", value=str(data.get("start_date", "")), placeholder="2022")
        with c2:
            data["end_date"] = st.text_input("End date", value=str(data.get("end_date", "")), placeholder="Present or 2026")
        data["is_current"] = st.checkbox("Current role", value=bool(data.get("is_current", False)))
        data["achievements"] = st.text_area(
            "Achievements / bullets",
            value=str(data.get("achievements", "")),
            height=220,
            placeholder="- Led shifts and improved operations`n- Managed customer-facing workflow"
        )

    elif section_key == "education":
        data["degree"] = st.text_input("Degree", value=str(data.get("degree", "")), placeholder="B.Sc.")
        data["field"] = st.text_input("Field", value=str(data.get("field", "")), placeholder="Information Systems")
        data["institution"] = st.text_input("Institution", value=str(data.get("institution", "")))
        data["location"] = st.text_input("Location", value=str(data.get("location", "")))
        c1, c2 = st.columns(2)
        with c1:
            data["start_year"] = st.text_input("Start year", value=str(data.get("start_year", "")))
        with c2:
            data["end_year"] = st.text_input("End year", value=str(data.get("end_year", "")))
        data["notes"] = st.text_area("Notes", value=str(data.get("notes", "")), height=120)

    elif section_key == "skills":
        data["category"] = st.text_input("Category", value=str(data.get("category", "")), placeholder="Programming / BI / Tools")
        data["items"] = st.text_area("Items", value=str(data.get("items", "")), height=120, placeholder="Python, SQL, Power BI, Streamlit")

    elif section_key == "languages":
        data["language"] = st.text_input("Language", value=str(data.get("language", "")), placeholder="English")
        data["proficiency"] = st.text_input("Proficiency", value=str(data.get("proficiency", "")), placeholder="Fluent")

    computed_title = make_default_title(section_key, data)
    if auto_title:
        st.text_input("Generated title", value=computed_title, disabled=True)
        title = computed_title
    else:
        title = st.text_input("Title", value=manual_title_default)

    tags = st.text_input("Tags", value=tags, placeholder="leadership, BI, analytics")
    sort_order = st.number_input("Sort order", min_value=0, step=1, value=int(sort_order))
    is_active = st.checkbox("Active", value=is_active)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save block", type="primary", use_container_width=True):
            try:
                block_id = save_cv_content_block(
                    conn=conn,
                    language_code=language_code,
                    section_key=section_key,
                    title=title,
                    data=data,
                    tags=tags,
                    is_active=is_active,
                    sort_order=int(sort_order),
                    block_id=selected_id,
                )
                st.success(f"Saved block #{block_id}")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    with c2:
        if st.button("Delete block", disabled=(selected_id is None), use_container_width=True):
            delete_cv_content_block(conn, int(selected_id))
            st.success(f"Deleted block #{selected_id}")
            st.rerun()

with right:
    st.subheader("Saved blocks")

    show_active_only = st.toggle("Show active only", value=True)
    view_lang = st.selectbox(
        "View language",
        options=["all", "en", "he"],
        format_func=lambda x: {"all": "All", "en": "English", "he": "Hebrew"}.get(x, x),
        index=0,
    )

    view_df = fetch_cv_content_blocks(conn, active_only=show_active_only)

    if view_lang != "all" and not view_df.empty:
        view_df = view_df[view_df["language_code"].astype(str).str.lower().eq(view_lang)]

    if view_df.empty:
        st.info("No saved blocks yet.")
    else:
        for lang_code, lang_group in view_df.groupby("language_code", sort=True):
            st.markdown(f"### {LANGUAGE_OPTIONS.get(lang_code, lang_code)}")
            for sec_key, sec_group in lang_group.groupby("section_key", sort=True):
                st.markdown(f"**{SECTION_OPTIONS.get(sec_key, sec_key.title())}**")
                sec_group = sec_group.sort_values(["sort_order", "updated_at", "id"], ascending=[True, False, False])
                for row in sec_group.itertuples(index=False):
                    active_mark = "" if int(row.is_active or 0) == 1 else " [inactive]"
                    with st.expander(f"#{int(row.id)} | {str(row.title or '').strip()}{active_mark}", expanded=False):
                        if str(row.tags or "").strip():
                            st.caption(f"Tags: {row.tags}")
                        st.caption(f"Sort order: {int(row.sort_order or 0)}")
                        st.code(str(row.content or "").strip(), language=None)
