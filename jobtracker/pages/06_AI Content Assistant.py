import json
import os
import re

import streamlit as st

from lib.ui import *
from openai import OpenAI

from lib import db as dbmod

get_conn = dbmod.get_conn
init_db = dbmod.init_db

save_cv_content_block = getattr(dbmod, "save_cv_content_block", None)
fetch_cv_content_blocks = getattr(dbmod, "fetch_cv_content_blocks", None)

st.set_page_config(page_title="AI Content Assistant", layout="wide")

inject_global_css()
sidebar_brand()
st.title("AI Content Assistant")
st.caption("Paste messy source text, let AI extract structured reusable blocks, review them, and save them into English, Hebrew, or both.")

api_key = os.environ.get("OPENAI_API_KEY", "").strip()
client = OpenAI(api_key=api_key) if api_key else None
MODEL_NAME = "gpt-4.1-mini"

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

OUTPUT_MODE_OPTIONS = {
    "source_only": "Source language only",
    "english_only": "English only",
    "hebrew_only": "Hebrew only",
    "both": "English and Hebrew",
}

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

def default_title(section_key: str, data: dict):
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
        return str(data.get("category", "")).strip() or "Skills"

    if section_key == "languages":
        return str(data.get("language", "")).strip() or "Language"

    return "Block"

def normalize_json_object(text: str):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("Could not find JSON object in model output")
    return json.loads(match.group(0))

def normalize_candidate(item: dict, fallback_language: str, forced_section: str | None):
    if not isinstance(item, dict):
        item = {}

    section_key = str(item.get("section_key", forced_section or "summary")).strip().lower()
    if section_key not in SECTION_OPTIONS:
        section_key = forced_section or "summary"

    language_code = str(item.get("language_code", fallback_language)).strip().lower()
    if language_code not in LANGUAGE_OPTIONS:
        language_code = fallback_language if fallback_language in LANGUAGE_OPTIONS else "en"

    data = item.get("data", {})
    if not isinstance(data, dict):
        data = {}

    template = empty_data(section_key)
    merged = template.copy()
    for k in template.keys():
        if k in data:
            merged[k] = data[k]

    title = str(item.get("title", "")).strip() or default_title(section_key, merged)
    tags = item.get("tags", [])
    if isinstance(tags, list):
        tags = ", ".join([str(x).strip() for x in tags if str(x).strip()])
    else:
        tags = str(tags or "").strip()

    pair_key = str(item.get("pair_key", "")).strip()

    return {
        "section_key": section_key,
        "language_code": language_code,
        "title": title,
        "tags": tags,
        "sort_order": int(item.get("sort_order", 0) or 0),
        "is_active": bool(item.get("is_active", True)),
        "data": merged,
        "pair_key": pair_key,
    }

def build_extraction_system_prompt(mode: str, target_section: str | None):
    section_instruction = "Detect the best section for each item."
    if mode == "targeted" and target_section:
        section_instruction = f"Convert all valid content into section_key='{target_section}' only."

    return f"""
You are a CV content extraction engine.

Your job:
- Read messy source text and convert it into structured reusable CV content blocks.
- Extract only facts that appear in the source text.
- Do not invent companies, dates, technologies, achievements, links, degree names, or proficiency levels.
- Split content into separate reusable entries where appropriate.
- {section_instruction}

Return ONLY valid JSON with this exact shape:
{{
  "items": [
    {{
      "section_key": "summary|experience|projects|education|skills|languages",
      "language_code": "en|he",
      "title": "short browsing title",
      "tags": ["optional", "tags"],
      "sort_order": 0,
      "is_active": true,
      "data": {{}}
    }}
  ]
}}

Allowed per-section data shapes:

summary:
{{ "summary": "..." }}

projects:
{{
  "project_name": "...",
  "tools": "...",
  "period": "...",
  "description": "...",
  "github_link": "...",
  "demo_link": "..."
}}

experience:
{{
  "employer": "...",
  "location": "...",
  "role": "...",
  "start_date": "...",
  "end_date": "...",
  "is_current": true,
  "achievements": "bullet-like plain text lines"
}}

education:
{{
  "degree": "...",
  "field": "...",
  "institution": "...",
  "location": "...",
  "start_year": "...",
  "end_year": "...",
  "notes": "..."
}}

skills:
{{
  "category": "...",
  "items": "comma-separated or line-separated skills"
}}

languages:
{{
  "language": "...",
  "proficiency": "..."
}}

Important factual rules:
- If the source says Information Systems, keep Information Systems.
- Never rewrite Information Systems as Computer Science.
- If language is Hebrew and the degree is Information Systems, use מערכות מידע, not מדעי המחשב.
- Keep GitHub/demo links only if they are explicitly present in the source.
- If dates are unclear, leave them blank rather than inventing them.

Output only JSON.
No markdown.
No explanations.
""".strip()

def build_extraction_user_prompt(source_text: str, notes: str, language_hint: str):
    return f"""
Language hint: {language_hint}

Optional user notes:
{notes or "None"}

SOURCE TEXT:
{source_text}
""".strip()

def build_translation_system_prompt(target_language: str):
    target_name = "English" if target_language == "en" else "Hebrew"
    return f"""
You are a structured CV content block translator.

Translate structured CV content block data into {target_name}.

Rules:
- Return ONLY valid JSON.
- Preserve the same list length, section_key, pair_key, tags, sort_order, and is_active values.
- Only translate fields inside title and data.
- Do not invent facts.
- Preserve links exactly.
- Preserve technologies and brand names naturally, such as Python, SQL, Power BI, Git, Streamlit.
- If translating Information Systems into Hebrew, use מערכות מידע.
- Never translate Information Systems into Computer Science or מדעי המחשב.
- If translating Hebrew מערכות מידע into English, use Information Systems.
- Keep dates as they are unless a direct script translation is needed.
- Keep the same shape for each section.

Return JSON in this exact shape:
{{
  "items": [
    {{
      "section_key": "...",
      "language_code": "{target_language}",
      "title": "...",
      "tags": "comma, separated, tags",
      "sort_order": 0,
      "is_active": true,
      "pair_key": "...",
      "data": {{}}
    }}
  ]
}}
""".strip()

def build_translation_user_prompt(items: list[dict], target_language: str):
    return f"""
Translate these structured CV content blocks to target language: {target_language}

{json.dumps({"items": items}, ensure_ascii=False, indent=2)}
""".strip()

def translate_candidates(items: list[dict], target_language: str):
    if not items:
        return []

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": build_translation_system_prompt(target_language)},
            {"role": "user", "content": build_translation_user_prompt(items, target_language)},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    parsed = normalize_json_object(resp.choices[0].message.content)
    raw_items = parsed.get("items", [])
    if not isinstance(raw_items, list):
        raw_items = []
    return [normalize_candidate(x, target_language, None) for x in raw_items]

def render_candidate_editor(idx: int, candidate: dict):
    st.markdown(f"### Candidate #{idx + 1}")

    c1, c2 = st.columns(2)
    with c1:
        candidate["language_code"] = st.selectbox(
            "Language",
            options=list(LANGUAGE_OPTIONS.keys()),
            index=list(LANGUAGE_OPTIONS.keys()).index(candidate["language_code"]) if candidate["language_code"] in LANGUAGE_OPTIONS else 0,
            format_func=lambda x: LANGUAGE_OPTIONS[x],
            key=f"cand_lang_{idx}",
        )
    with c2:
        candidate["section_key"] = st.selectbox(
            "Section",
            options=list(SECTION_OPTIONS.keys()),
            index=list(SECTION_OPTIONS.keys()).index(candidate["section_key"]) if candidate["section_key"] in SECTION_OPTIONS else 0,
            format_func=lambda x: SECTION_OPTIONS[x],
            key=f"cand_section_{idx}",
        )

    section_key = candidate["section_key"]
    data = candidate.get("data", {}) or {}
    template = empty_data(section_key)

    for k, v in template.items():
        if k not in data:
            data[k] = v

    st.caption(f"Pair key: {candidate.get('pair_key', '') or '-'}")

    if section_key == "summary":
        data["summary"] = st.text_area("Summary", value=str(data.get("summary", "")), height=140, key=f"cand_summary_{idx}")

    elif section_key == "projects":
        data["project_name"] = st.text_input("Project name", value=str(data.get("project_name", "")), key=f"cand_project_name_{idx}")
        data["tools"] = st.text_input("Tools / tech stack", value=str(data.get("tools", "")), key=f"cand_tools_{idx}")
        data["period"] = st.text_input("Year / period", value=str(data.get("period", "")), key=f"cand_period_{idx}")
        data["description"] = st.text_area("Description", value=str(data.get("description", "")), height=160, key=f"cand_project_desc_{idx}")
        data["github_link"] = st.text_input("GitHub link", value=str(data.get("github_link", "")), key=f"cand_github_{idx}")
        data["demo_link"] = st.text_input("Demo / live link", value=str(data.get("demo_link", "")), key=f"cand_demo_{idx}")

    elif section_key == "experience":
        data["employer"] = st.text_input("Employer", value=str(data.get("employer", "")), key=f"cand_employer_{idx}")
        data["location"] = st.text_input("Location", value=str(data.get("location", "")), key=f"cand_location_{idx}")
        data["role"] = st.text_input("Role", value=str(data.get("role", "")), key=f"cand_role_{idx}")
        c3, c4 = st.columns(2)
        with c3:
            data["start_date"] = st.text_input("Start date", value=str(data.get("start_date", "")), key=f"cand_start_{idx}")
        with c4:
            data["end_date"] = st.text_input("End date", value=str(data.get("end_date", "")), key=f"cand_end_{idx}")
        data["is_current"] = st.checkbox("Current role", value=bool(data.get("is_current", False)), key=f"cand_current_{idx}")
        data["achievements"] = st.text_area("Achievements / bullets", value=str(data.get("achievements", "")), height=180, key=f"cand_ach_{idx}")

    elif section_key == "education":
        data["degree"] = st.text_input("Degree", value=str(data.get("degree", "")), key=f"cand_degree_{idx}")
        data["field"] = st.text_input("Field", value=str(data.get("field", "")), key=f"cand_field_{idx}")
        data["institution"] = st.text_input("Institution", value=str(data.get("institution", "")), key=f"cand_institution_{idx}")
        data["location"] = st.text_input("Location", value=str(data.get("location", "")), key=f"cand_ed_location_{idx}")
        c3, c4 = st.columns(2)
        with c3:
            data["start_year"] = st.text_input("Start year", value=str(data.get("start_year", "")), key=f"cand_start_year_{idx}")
        with c4:
            data["end_year"] = st.text_input("End year", value=str(data.get("end_year", "")), key=f"cand_end_year_{idx}")
        data["notes"] = st.text_area("Notes", value=str(data.get("notes", "")), height=120, key=f"cand_notes_{idx}")

    elif section_key == "skills":
        data["category"] = st.text_input("Category", value=str(data.get("category", "")), key=f"cand_skill_cat_{idx}")
        data["items"] = st.text_area("Items", value=str(data.get("items", "")), height=120, key=f"cand_skill_items_{idx}")

    elif section_key == "languages":
        data["language"] = st.text_input("Language", value=str(data.get("language", "")), key=f"cand_language_{idx}")
        data["proficiency"] = st.text_input("Proficiency", value=str(data.get("proficiency", "")), key=f"cand_prof_{idx}")

    candidate["data"] = data

    auto_title = default_title(section_key, data)
    candidate["title"] = st.text_input("Title", value=str(candidate.get("title", "") or auto_title), key=f"cand_title_{idx}")
    candidate["tags"] = st.text_input("Tags", value=str(candidate.get("tags", "")), key=f"cand_tags_{idx}")
    candidate["sort_order"] = int(st.number_input("Sort order", min_value=0, step=1, value=int(candidate.get("sort_order", 0)), key=f"cand_sort_{idx}"))
    candidate["is_active"] = st.checkbox("Active", value=bool(candidate.get("is_active", True)), key=f"cand_active_{idx}")

    return candidate

conn = get_conn()
init_db(conn)

if not callable(save_cv_content_block):
    st.error("save_cv_content_block is not available in lib.db yet. The assistant page needs the structured content block system first.")
    st.stop()

if not api_key:
    st.warning('Set OPENAI_API_KEY and restart PowerShell. Example: setx OPENAI_API_KEY "YOUR_KEY"')

mode = st.radio(
    "Extraction mode",
    options=["Auto-detect sections", "Target one section"],
    horizontal=True,
)

language_hint = st.selectbox(
    "Source language hint",
    options=["auto", "en", "he"],
    format_func=lambda x: {"auto": "Auto-detect", "en": "English", "he": "Hebrew"}.get(x, x),
    index=0,
)

output_mode = st.selectbox(
    "Output blocks",
    options=list(OUTPUT_MODE_OPTIONS.keys()),
    format_func=lambda x: OUTPUT_MODE_OPTIONS[x],
    index=3,
)

target_section = None
if mode == "Target one section":
    target_section = st.selectbox(
        "Target section",
        options=list(SECTION_OPTIONS.keys()),
        format_func=lambda x: SECTION_OPTIONS[x],
        index=1,
    )

notes = st.text_area(
    "Optional extraction notes",
    height=90,
    placeholder="Example: split projects separately, keep BI skills grouped, preserve wording where possible...",
)

source_text = st.text_area(
    "Paste raw source text",
    height=260,
    placeholder="Paste old CV text, LinkedIn About, project notes, experience bullets, Hebrew notes, English notes, or mixed messy text here...",
)

generate = st.button("Analyze and extract candidates", type="primary", disabled=(not api_key), use_container_width=True)

if generate:
    if not source_text.strip():
        st.error("Source text is empty.")
        st.stop()

    extraction_system = build_extraction_system_prompt(
        mode="targeted" if mode == "Target one section" else "auto",
        target_section=target_section,
    )
    extraction_user = build_extraction_user_prompt(source_text.strip(), notes.strip(), language_hint)

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": extraction_system},
                {"role": "user", "content": extraction_user},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        parsed = normalize_json_object(resp.choices[0].message.content)
        items = parsed.get("items", [])
        if not isinstance(items, list):
            items = []

        detected_fallback = "en" if language_hint == "auto" else language_hint
        normalized_source = [normalize_candidate(x, detected_fallback, target_section) for x in items]

        # ensure pair keys
        for i, item in enumerate(normalized_source, start=1):
            if not str(item.get("pair_key", "")).strip():
                item["pair_key"] = f"pair_{i}"

        final_candidates = []

        if output_mode == "source_only":
            final_candidates = normalized_source

        elif output_mode == "english_only":
            if normalized_source:
                if all(x["language_code"] == "en" for x in normalized_source):
                    final_candidates = normalized_source
                else:
                    final_candidates = translate_candidates(normalized_source, "en")

        elif output_mode == "hebrew_only":
            if normalized_source:
                if all(x["language_code"] == "he" for x in normalized_source):
                    final_candidates = normalized_source
                else:
                    final_candidates = translate_candidates(normalized_source, "he")

        elif output_mode == "both":
            english_items = []
            hebrew_items = []

            if normalized_source:
                if all(x["language_code"] == "en" for x in normalized_source):
                    english_items = normalized_source
                    hebrew_items = translate_candidates(normalized_source, "he")
                elif all(x["language_code"] == "he" for x in normalized_source):
                    hebrew_items = normalized_source
                    english_items = translate_candidates(normalized_source, "en")
                else:
                    english_items = [x for x in normalized_source if x["language_code"] == "en"]
                    hebrew_items = [x for x in normalized_source if x["language_code"] == "he"]

                    if english_items and not hebrew_items:
                        hebrew_items = translate_candidates(english_items, "he")
                    elif hebrew_items and not english_items:
                        english_items = translate_candidates(hebrew_items, "en")

            final_candidates = english_items + hebrew_items

        if not final_candidates:
            st.warning("AI returned no usable candidate blocks.")
        else:
            st.session_state["ai_content_candidates"] = final_candidates
            st.success(f"Prepared {len(final_candidates)} candidate block(s). Review them below before saving.")
    except Exception as e:
        st.error(f"Extraction failed: {e}")

candidates = st.session_state.get("ai_content_candidates", [])

if candidates:
    st.divider()
    st.subheader("Review and save candidates")

    # grouped display by pair_key
    grouped = {}
    for idx, candidate in enumerate(candidates):
        key = str(candidate.get("pair_key", "") or f"ungrouped_{idx}")
        grouped.setdefault(key, []).append((idx, candidate))

    for pair_key, items in grouped.items():
        with st.container(border=True):
            st.markdown(f"## Pair group: {pair_key}")
            for idx, candidate in items:
                updated = render_candidate_editor(idx, candidate)
                st.session_state["ai_content_candidates"][idx] = updated

                c1, c2 = st.columns(2)
                with c1:
                    if st.button(f"Save candidate #{idx + 1}", key=f"save_candidate_{idx}", use_container_width=True):
                        try:
                            block_id = save_cv_content_block(
                                conn=conn,
                                language_code=updated["language_code"],
                                section_key=updated["section_key"],
                                title=updated["title"],
                                data=updated["data"],
                                tags=updated["tags"],
                                is_active=updated["is_active"],
                                sort_order=updated["sort_order"],
                            )
                            st.success(f"Saved candidate #{idx + 1} as block #{block_id}")
                        except Exception as e:
                            st.error(f"Save failed: {e}")

                with c2:
                    if st.button(f"Discard candidate #{idx + 1}", key=f"discard_candidate_{idx}", use_container_width=True):
                        st.session_state["ai_content_candidates"].pop(idx)
                        st.rerun()

            if st.button(f"Save all in pair group {pair_key}", key=f"save_pair_{pair_key}", use_container_width=True):
                saved_ids = []
                try:
                    for idx, candidate in items:
                        current = st.session_state["ai_content_candidates"][idx]
                        block_id = save_cv_content_block(
                            conn=conn,
                            language_code=current["language_code"],
                            section_key=current["section_key"],
                            title=current["title"],
                            data=current["data"],
                            tags=current["tags"],
                            is_active=current["is_active"],
                            sort_order=current["sort_order"],
                        )
                        saved_ids.append(block_id)
                    st.success(f"Saved pair group {pair_key}: blocks {saved_ids}")
                except Exception as e:
                    st.error(f"Save-all failed: {e}")

if callable(fetch_cv_content_blocks):
    st.divider()
    st.subheader("Recent saved blocks")

    try:
        recent_df = fetch_cv_content_blocks(conn, active_only=False)
        if recent_df.empty:
            st.info("No saved content blocks yet.")
        else:
            recent_df = recent_df.sort_values(["updated_at", "id"], ascending=[False, False]).head(10)
            for row in recent_df.itertuples(index=False):
                with st.expander(f"#{int(row.id)} | {str(row.title or '').strip()} | {LANGUAGE_OPTIONS.get(str(row.language_code), row.language_code)} | {SECTION_OPTIONS.get(str(row.section_key), row.section_key)}", expanded=False):
                    st.caption(f"Tags: {str(row.tags or '').strip() or '-'}")
                    st.code(str(row.content or "").strip(), language=None)
    except Exception as e:
        st.warning(f"Could not load recent blocks: {e}")
