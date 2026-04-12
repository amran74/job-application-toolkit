import os
import json
import re
import shutil
from datetime import date

import streamlit as st

from lib.ui import *
from openai import OpenAI

from lib import db as dbmod
from lib.pdf_export import export_cv_pdf, export_cv_pdf_he, export_cover_letter_pdf
from lib.ats import coverage

get_conn = dbmod.get_conn
init_db = dbmod.init_db
fetch_jobs = dbmod.fetch_jobs
get_job = dbmod.get_job
save_cv_version = dbmod.save_cv_version
update_cv_paths = dbmod.update_cv_paths
get_setting = dbmod.get_setting

fetch_cv_content_blocks = getattr(dbmod, "fetch_cv_content_blocks", None)
build_cv_source_text = getattr(dbmod, "build_cv_source_text", None)

st.set_page_config(page_title="AI CV Generator", layout="wide")

inject_global_css()
sidebar_brand()
st.title("AI CV Generator")
st.caption("Reworked AI CV flow for the current app: baseline CV, saved blocks, English/Hebrew PDFs, and versioned output.")

api_key = os.environ.get("OPENAI_API_KEY", "").strip()
client = OpenAI(api_key=api_key) if api_key else None

MODEL_NAME = "gpt-4.1-mini"
SECTION_SPECS = [
    ("summary", "Summary"),
    ("experience", "Experience"),
    ("projects", "Projects"),
    ("education", "Education"),
    ("skills", "Skills"),
    ("languages", "Languages"),
]

def clamp_text(s: str, max_chars: int) -> str:
    return (s or "").strip()[:max_chars]

def extract_json_object(text: str) -> dict:
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

def normalize_bundle(data, headline_override: str, include_cover: bool):
    if not isinstance(data, dict):
        data = {"cv": {"summary": str(data)}}

    cv = data.get("cv") or {}
    cover = data.get("cover_letter") or {}
    notes = data.get("notes") or {}

    if isinstance(cv, str):
        cv = {
            "headline": headline_override or "",
            "summary": cv,
            "experience": "",
            "skills": "",
            "languages": "",
            "education": "",
            "projects": "",
        }

    cv = {
        "headline": str(cv.get("headline", headline_override or "") or ""),
        "summary": str(cv.get("summary", "") or ""),
        "experience": str(cv.get("experience", "") or ""),
        "skills": str(cv.get("skills", "") or ""),
        "languages": str(cv.get("languages", "") or ""),
        "education": str(cv.get("education", "") or ""),
        "projects": str(cv.get("projects", "") or ""),
    }

    if not include_cover:
        cover = {"subject": "", "body": ""}
    elif isinstance(cover, str):
        cover = {"subject": "", "body": cover}
    elif not isinstance(cover, dict):
        cover = {"subject": "", "body": ""}
    else:
        cover = {
            "subject": str(cover.get("subject", "") or ""),
            "body": str(cover.get("body", "") or ""),
        }

    if not isinstance(notes, dict):
        notes = {}

    for key in ["keywords_used", "changes_made", "warnings"]:
        val = notes.get(key, [])
        if not isinstance(val, list):
            val = [str(val)] if str(val).strip() else []
        notes[key] = [str(x) for x in val if str(x).strip()]

    return cv, cover, notes

def ensure_headed_multiblock(text: str, fallback_heading: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    lines = [x.rstrip() for x in text.splitlines() if x.strip()]
    if not lines:
        return ""
    first = lines[0].strip()
    looks_like_heading = not first.startswith("-") and not first.startswith(chr(8226)) and len(first) < 140
    if looks_like_heading:
        return "\n".join(lines)
    out = [fallback_heading]
    for line in lines:
        s = line.strip()
        if s.startswith("-") or s.startswith(chr(8226)):
            out.append(chr(8226) + " " + s.lstrip("-" + chr(8226) + " ").strip())
        else:
            out.append(chr(8226) + " " + s)
    return "\n".join(out)

def split_languages_from_skills(cv: dict) -> dict:
    skills = (cv.get("skills", "") or "").strip()
    languages = (cv.get("languages", "") or "").strip()
    if languages:
        return cv
    kept = []
    extracted = []
    for line in skills.splitlines():
        low = line.lower().strip()
        if low.startswith("languages:"):
            rhs = line.split(":", 1)[1].strip()
            if rhs:
                extracted.extend([x.strip() for x in rhs.split(",") if x.strip()])
        else:
            kept.append(line)
    if extracted:
        cv["skills"] = "\n".join([x for x in kept if x.strip()])
        cv["languages"] = "\n".join(extracted)
    return cv

def postprocess_cv(cv: dict, company: str, role: str) -> dict:
    exp_heading = "Experience"
    if company and role:
        exp_heading = f"{company} - {role}"
    elif role:
        exp_heading = role
    elif company:
        exp_heading = company
    cv["experience"] = ensure_headed_multiblock(cv.get("experience", ""), exp_heading)
    cv["projects"] = ensure_headed_multiblock(cv.get("projects", ""), "Selected Project")
    return split_languages_from_skills(cv)

def build_prompt(source_text: str, jd_text: str, company: str, role: str, archetype: str, tone: str, length: str, custom_notes: str):
    system_rules = f"""
You are a CV tailoring engine.

Use only source material provided by the user.
Do not invent employers, projects, dates, degrees, links, or achievements.
Return only valid JSON with this shape:

{{
  "cv": {{
    "headline": "",
    "summary": "",
    "experience": "",
    "skills": "",
    "languages": "",
    "education": "",
    "projects": ""
  }},
  "cover_letter": {{
    "subject": "",
    "body": ""
  }},
  "notes": {{
    "keywords_used": [],
    "changes_made": [],
    "warnings": []
  }}
}}

Rules:
- experience must be a plain string with role headings and bullet lines
- projects must be a plain string with project headings and bullet lines
- languages must be separate from skills
- preserve Information Systems as Information Systems, never Computer Science
- tone: {tone}
- archetype: {archetype}
- target length: {length}

User notes:
{custom_notes or "None"}
""".strip()

    user_input = f"""
Company: {company or ""}
Role: {role or ""}

JOB DESCRIPTION:
{jd_text}

SOURCE MATERIAL:
{source_text}
""".strip()

    return system_rules, user_input

def build_hebrew_translation_prompt(cv_en: dict, hebrew_reference_text: str = ""):
    system_rules = """
Translate the English CV JSON into professional Hebrew.
Return only valid JSON.
Preserve the same keys.
Do not invent facts.
Keep Information Systems as מערכות מידע, never מדעי המחשב.
""".strip()

    reference_block = ""
    if (hebrew_reference_text or "").strip():
        reference_block = f"\n\nOptional Hebrew wording reference:\n{hebrew_reference_text}"

    user_input = f"""
Translate this CV JSON to Hebrew.
Keep the same keys.
Do not add new facts.{reference_block}

{json.dumps(cv_en, ensure_ascii=False, indent=2)}
""".strip()
    return system_rules, user_input

def normalize_hebrew_cv(data) -> dict:
    if not isinstance(data, dict):
        data = {}
    return {
        "headline": str(data.get("headline", "") or ""),
        "summary": str(data.get("summary", "") or ""),
        "experience": str(data.get("experience", "") or ""),
        "skills": str(data.get("skills", "") or ""),
        "languages": str(data.get("languages", "") or ""),
        "education": str(data.get("education", "") or ""),
        "projects": str(data.get("projects", "") or ""),
    }

def enforce_hebrew_degree_truth(cv: dict) -> dict:
    replacements = {
        "מדעי המחשב": "מערכות מידע",
        "תואר במדעי המחשב": "תואר במערכות מידע",
        "תואר ראשון במדעי המחשב": "תואר ראשון במערכות מידע",
        "computer science": "information systems",
    }
    for key in ["headline", "summary", "experience", "skills", "languages", "education", "projects"]:
        val = str(cv.get(key, "") or "")
        for bad, good in replacements.items():
            val = re.sub(re.escape(bad), good, val, flags=re.IGNORECASE)
        cv[key] = val
    return cv

def archive_copy(src_path: str, kind: str, version_id: int):
    archive_dir = os.path.join("jobtracker", "exports", "_archive", kind)
    os.makedirs(archive_dir, exist_ok=True)
    base = os.path.basename(src_path)
    archived = os.path.join(archive_dir, f"v{version_id}_{base}")
    shutil.copy2(src_path, archived)
    return archived

def make_block_option_map(df_blocks, section_key: str, language_code: str):
    if df_blocks is None or getattr(df_blocks, "empty", True):
        return {}
    sub = df_blocks.copy()
    sub = sub[
        sub["section_key"].astype(str).str.lower().eq(section_key) &
        sub["language_code"].astype(str).str.lower().eq(language_code)
    ].copy()
    if "is_active" in sub.columns:
        sub = sub[sub["is_active"].fillna(0).astype(int).eq(1)]
    if sub.empty:
        return {}
    sort_cols = [c for c in ["sort_order", "title", "id"] if c in sub.columns]
    if sort_cols:
        sub = sub.sort_values(sort_cols)
    out = {}
    for row in sub.itertuples(index=False):
        out[f"#{int(row.id)} | {str(row.title or '').strip()}"] = int(row.id)
    return out

def assemble_saved_text(conn, block_ids, language_code: str):
    if not block_ids or not callable(build_cv_source_text):
        return ""
    try:
        return build_cv_source_text(conn, block_ids, language_code=language_code)
    except Exception:
        return ""

conn = get_conn()
init_db(conn)
df_jobs = fetch_jobs(conn)

if df_jobs.empty:
    st.info("No jobs found. Add a job first.")
    st.stop()

baseline_saved = get_setting(conn, "baseline_cv_text") or ""
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
content_blocks_available = callable(fetch_cv_content_blocks) and callable(build_cv_source_text)
if content_blocks_available:
    try:
        blocks_df = fetch_cv_content_blocks(conn, active_only=True)
    except Exception as e:
        content_blocks_available = False
        st.warning(f"Saved content blocks unavailable: {e}")

choices = [f"#{r.id} | {r.company} - {r.role}" for r in df_jobs.itertuples(index=False)]
pick = st.selectbox("Select job", choices)
job_id = int(pick.split("|")[0].strip().replace("#", ""))
job = get_job(conn, job_id) or {}

st.subheader("Header")
c1, c2, c3 = st.columns(3)
with c1:
    name = st.text_input("Name", value=profile["name"])
    headline_override = st.text_input("Headline override", value=profile["headline"])
with c2:
    email = st.text_input("Email", value=profile["email"])
    phone = st.text_input("Phone", value=profile["phone"])
with c3:
    github = st.text_input("GitHub URL", value=profile["github_url"])
    linkedin = st.text_input("LinkedIn URL", value=profile["linkedin_url"])

website = st.text_input("Website URL", value=profile["website_url"])
location = st.text_input("Location", value=(job.get("location") or profile["location"] or ""))

contacts = {
    "email": email.strip(),
    "phone": phone.strip(),
    "github_url": github.strip(),
    "linkedin_url": linkedin.strip(),
    "website_url": website.strip(),
    "location": location.strip(),
}

st.subheader("Inputs")
left, right = st.columns([1, 1], gap="large")

with left:
    company = st.text_input("Company", value=job.get("company") or "")
    role = st.text_input("Role title", value=job.get("role") or "")
    baseline_text = st.text_area("Baseline CV text", height=280, value=baseline_saved)

with right:
    jd_text = st.text_area("Job description", height=240, value=job.get("jd_text") or "")
    custom_notes = st.text_area("Custom notes for AI", height=120)

source_mode = "Baseline only"
selected_en_ids = []
selected_he_ids = []

if content_blocks_available:
    source_mode = st.selectbox("CV source", ["Baseline only", "Saved blocks only", "Baseline + saved blocks"], index=2)

    with st.expander("Saved English content blocks", expanded=(source_mode != "Baseline only")):
        for section_key, section_label in SECTION_SPECS:
            options_map = make_block_option_map(blocks_df, section_key, "en")
            picked = st.multiselect(f"English {section_label}", options=list(options_map.keys()), key=f"en_blocks_{section_key}")
            selected_en_ids.extend([options_map[x] for x in picked])

    with st.expander("Saved Hebrew content blocks", expanded=False):
        for section_key, section_label in SECTION_SPECS:
            options_map = make_block_option_map(blocks_df, section_key, "he")
            picked = st.multiselect(f"Hebrew {section_label}", options=list(options_map.keys()), key=f"he_blocks_{section_key}")
            selected_he_ids.extend([options_map[x] for x in picked])

saved_source_en = assemble_saved_text(conn, selected_en_ids, "en")
saved_source_he = assemble_saved_text(conn, selected_he_ids, "he")

archetype = st.selectbox("Archetype", ["Data/BI", "Marketing Analyst", "Ops/Management", "Fraud/Risk", "Custom"])
tone = st.selectbox("Tone", ["Concise", "Impact-driven", "Technical", "Leadership"])
length = st.selectbox("Length", ["1 page", "2 pages"])
include_cover = st.checkbox("Generate cover letter", value=True)

if st.button("Generate tailored CV package", type="primary", disabled=(not api_key), use_container_width=True):
    baseline_clean = (baseline_text or "").strip()
    saved_en_clean = (saved_source_en or "").strip()
    saved_he_clean = (saved_source_he or "").strip()

    parts = []
    if source_mode in ["Baseline only", "Baseline + saved blocks"] and baseline_clean:
        parts.append(baseline_clean)
    if source_mode in ["Saved blocks only", "Baseline + saved blocks"] and saved_en_clean:
        parts.append(saved_en_clean)

    assembled_source_text = "\n\n".join([x for x in parts if x.strip()]).strip()

    if not assembled_source_text:
        st.error("No CV source content available.")
        st.stop()

    if not jd_text.strip():
        st.error("Job description is empty.")
        st.stop()

    system_rules, user_input = build_prompt(
        source_text=clamp_text(assembled_source_text, 12000),
        jd_text=clamp_text(jd_text, 12000),
        company=company,
        role=role,
        archetype=archetype,
        tone=tone,
        length=length,
        custom_notes=custom_notes.strip(),
    )

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_rules},
                {"role": "user", "content": user_input},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        cv_en, cover_en, notes = normalize_bundle(extract_json_object(resp.choices[0].message.content), headline_override, include_cover)
        cv_en = postprocess_cv(cv_en, company, role)
    except Exception as e:
        st.error(f"English generation failed: {e}")
        st.stop()

    try:
        he_sys, he_user = build_hebrew_translation_prompt(cv_en, hebrew_reference_text=saved_he_clean)
        he_resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": he_sys},
                {"role": "user", "content": he_user},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        cv_he = enforce_hebrew_degree_truth(normalize_hebrew_cv(extract_json_object(he_resp.choices[0].message.content)))
    except Exception as e:
        st.error(f"Hebrew translation failed: {e}")
        st.stop()

    try:
        ats_score, matched, missing = coverage(
            "\n\n".join([
                cv_en.get("headline", ""),
                cv_en.get("summary", ""),
                cv_en.get("experience", ""),
                cv_en.get("skills", ""),
                cv_en.get("projects", ""),
                cv_en.get("education", ""),
                cv_en.get("languages", ""),
            ]),
            jd_text
        )
    except Exception:
        ats_score, matched, missing = 0, [], []

    version_id = save_cv_version(
        conn=conn,
        job_id=job_id,
        model=MODEL_NAME,
        archetype=archetype,
        tone=tone,
        length=length,
        include_cover=include_cover,
        cv_json=json.dumps(cv_en, ensure_ascii=False),
        cover_json=json.dumps(cover_en, ensure_ascii=False),
        notes_json=json.dumps({
            "keywords_used": notes.get("keywords_used", []),
            "changes_made": notes.get("changes_made", []),
            "warnings": notes.get("warnings", []),
            "ats_score": ats_score,
            "matched_keywords": matched,
            "missing_keywords": missing,
            "source_mode": source_mode,
        }, ensure_ascii=False),
        cv_pdf_path=None,
        cover_pdf_path=None,
    )

    out_dir = os.path.join("jobtracker", "exports", f"job_{job_id}")
    os.makedirs(out_dir, exist_ok=True)

    today = date.today().isoformat()
    safe_company = "".join([c for c in (company or "company") if c.isalnum() or c in ("_", "-")])[:24]
    safe_role = "".join([c for c in (role or "role") if c.isalnum() or c in ("_", "-")])[:24]

    cv_pdf_en = os.path.join(out_dir, f"cv_en_v{version_id}_{safe_company}_{safe_role}_{today}.pdf")
    cv_pdf_he = os.path.join(out_dir, f"cv_he_v{version_id}_{safe_company}_{safe_role}_{today}.pdf")
    cl_pdf_en = os.path.join(out_dir, f"cover_en_v{version_id}_{safe_company}_{safe_role}_{today}.pdf")

    headline_en = headline_override.strip() or cv_en.get("headline", "")
    headline_he = cv_he.get("headline", "")

    sections_en = [
        ("Experience", cv_en.get("experience", ""), "bullets"),
        ("Selected Projects", cv_en.get("projects", ""), "bullets"),
        ("Technical Skills", cv_en.get("skills", ""), "text"),
        ("Education", cv_en.get("education", ""), "text"),
        ("Languages", cv_en.get("languages", ""), "text"),
    ]

    sections_he = [
        ("Experience", cv_he.get("experience", ""), "bullets"),
        ("Projects", cv_he.get("projects", ""), "bullets"),
        ("Skills", cv_he.get("skills", ""), "text"),
        ("Education", cv_he.get("education", ""), "text"),
        ("Languages", cv_he.get("languages", ""), "text"),
    ]

    try:
        export_cv_pdf(cv_pdf_en, name, headline_en, contacts, cv_en.get("summary", ""), sections_en)
        export_cv_pdf_he(cv_pdf_he, name, headline_he, contacts, cv_he.get("summary", ""), sections_he)

        archived_cv_en = archive_copy(cv_pdf_en, "cv", version_id)
        archived_cv_he = archive_copy(cv_pdf_he, "cv", version_id)

        cover_pdf_path = None
        archived_cover_en = None

        if include_cover and (cover_en.get("body", "").strip() or cover_en.get("subject", "").strip()):
            export_cover_letter_pdf(
                cl_pdf_en,
                name,
                contacts,
                cover_en.get("body", ""),
                headline=headline_en,
                date_str=str(date.today()),
            )
            cover_pdf_path = cl_pdf_en
            archived_cover_en = archive_copy(cl_pdf_en, "cover", version_id)

        update_cv_paths(conn, version_id, cv_pdf_path=cv_pdf_en, cover_pdf_path=cover_pdf_path)
    except Exception as e:
        st.error(f"PDF build failed: {e}")
        st.stop()

    st.session_state["ai_cv_result"] = {
        "version_id": version_id,
        "cv_en": cv_en,
        "cv_he": cv_he,
        "cover_en": cover_en,
        "notes": notes,
        "ats_score": ats_score,
        "matched": matched,
        "missing": missing,
        "cv_pdf_en": cv_pdf_en,
        "cv_pdf_he": cv_pdf_he,
        "cl_pdf_en": cl_pdf_en if include_cover and os.path.exists(cl_pdf_en) else "",
        "archived_cv_en": archived_cv_en,
        "archived_cv_he": archived_cv_he,
        "archived_cover_en": archived_cover_en or "",
    }

    st.success(f"Saved version #{version_id} and built the CV package.")

result = st.session_state.get("ai_cv_result")
if result:
    st.divider()
    st.subheader(f"Latest result: version #{result['version_id']}")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("ATS score", f"{int(result.get('ats_score', 0))}%")
    with c2:
        st.metric("Matched keywords", len(result.get("matched", [])))
    with c3:
        st.metric("Missing keywords", len(result.get("missing", [])))

    tabs = st.tabs(["English CV", "Hebrew CV", "Cover Letter", "ATS & Notes", "Downloads"])

    with tabs[0]:
        st.text(result["cv_en"].get("headline", ""))
        st.text(result["cv_en"].get("summary", ""))
        st.text(result["cv_en"].get("experience", ""))
        st.text(result["cv_en"].get("projects", ""))
        st.text(result["cv_en"].get("skills", ""))
        st.text(result["cv_en"].get("education", ""))
        st.text(result["cv_en"].get("languages", ""))

    with tabs[1]:
        st.text(result["cv_he"].get("headline", ""))
        st.text(result["cv_he"].get("summary", ""))
        st.text(result["cv_he"].get("experience", ""))
        st.text(result["cv_he"].get("projects", ""))
        st.text(result["cv_he"].get("skills", ""))
        st.text(result["cv_he"].get("education", ""))
        st.text(result["cv_he"].get("languages", ""))

    with tabs[2]:
        st.text(result["cover_en"].get("subject", ""))
        st.text(result["cover_en"].get("body", ""))

    with tabs[3]:
        st.write(result.get("matched", []))
        st.write(result.get("missing", []))
        st.write(result.get("notes", {}).get("changes_made", []))
        st.write(result.get("notes", {}).get("warnings", []))

    with tabs[4]:
        if os.path.exists(result["cv_pdf_en"]):
            with open(result["cv_pdf_en"], "rb") as f:
                st.download_button("Download English CV PDF", f, file_name=os.path.basename(result["cv_pdf_en"]), mime="application/pdf", use_container_width=True)
        if os.path.exists(result["cv_pdf_he"]):
            with open(result["cv_pdf_he"], "rb") as f:
                st.download_button("Download Hebrew CV PDF", f, file_name=os.path.basename(result["cv_pdf_he"]), mime="application/pdf", use_container_width=True)
        if result.get("cl_pdf_en") and os.path.exists(result["cl_pdf_en"]):
            with open(result["cl_pdf_en"], "rb") as f:
                st.download_button("Download English Cover PDF", f, file_name=os.path.basename(result["cl_pdf_en"]), mime="application/pdf", use_container_width=True)
