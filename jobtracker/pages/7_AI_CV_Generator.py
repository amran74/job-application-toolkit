import os
import json
import re
import shutil
from datetime import date
import streamlit as st
from openai import OpenAI

from lib.db import (
    get_conn, init_db, fetch_jobs, get_job,
    save_cv_version, update_cv_paths, get_setting
)
from lib.pdf_export import export_cv_pdf, export_cv_pdf_he, export_cover_letter_pdf
from lib.ats import coverage

st.set_page_config(page_title="AI CV Generator", layout="wide")
st.title("AI CV Generator")
st.caption("Generate a tailored English CV, Hebrew CV, and English cover letter from a selected job. Hebrew CV is exported as a file only and is not saved to the DB.")

api_key = os.environ.get("OPENAI_API_KEY", "").strip()
client = OpenAI(api_key=api_key) if api_key else None

if not api_key:
    st.warning('Set OPENAI_API_KEY and restart PowerShell. Example: setx OPENAI_API_KEY "YOUR_KEY"')

MODEL_NAME = "gpt-4.1-mini"


def clamp_text(s: str, max_chars: int) -> str:
    return (s or "").strip()[:max_chars]


def extract_json_object(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        raise ValueError("Model returned empty content")

    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except Exception:
        pass

    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("Could not find JSON object in model output")
    return json.loads(m.group(0))


def normalize_bundle(data, headline_override: str, include_cover: bool):
    if not isinstance(data, dict):
        data = {"cv": {"summary": str(data)}}

    cv = data.get("cv") or data.get("resume") or data.get("content") or {}
    cover = data.get("cover_letter") or data.get("cover") or {}
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

    if not isinstance(cv, dict):
        cv = {}

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

    notes = {
        "keywords_used": notes.get("keywords_used", []),
        "changes_made": notes.get("changes_made", []),
        "warnings": notes.get("warnings", []),
    }

    for k in ("keywords_used", "changes_made", "warnings"):
        if not isinstance(notes[k], list):
            notes[k] = [str(notes[k])] if str(notes[k]).strip() else []
        notes[k] = [str(x) for x in notes[k] if str(x).strip()]

    return cv, cover, notes


def ensure_headed_multiblock(text: str, fallback_heading: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""

    lines = [x.rstrip() for x in text.splitlines()]
    non_empty = [x for x in lines if x.strip()]
    if not non_empty:
        return ""

    first = non_empty[0].strip()
    looks_like_heading = (
        not first.startswith("•")
        and not first.startswith("-")
        and len(first) < 140
    )

    if looks_like_heading:
        return "\n".join(non_empty)

    bullets = []
    paras = []
    for line in non_empty:
        s = line.strip()
        if s.startswith("•") or s.startswith("-"):
            bullets.append("• " + s.lstrip("•- ").strip())
        else:
            paras.append(s)

    body = bullets if bullets else ["• " + x for x in paras]
    return fallback_heading + "\n" + "\n".join(body)


def split_languages_from_skills(cv: dict) -> dict:
    if not isinstance(cv, dict):
        return cv

    skills = (cv.get("skills", "") or "").strip()
    languages = (cv.get("languages", "") or "").strip()

    if languages:
        return cv

    lines = skills.splitlines()
    kept = []
    extracted = []

    for line in lines:
        low = line.lower().strip()
        if low.startswith("languages:"):
            rhs = line.split(":", 1)[1].strip()
            if rhs:
                pieces = [x.strip() for x in rhs.split(",") if x.strip()]
                rebuilt = []
                i = 0
                while i < len(pieces):
                    cur = pieces[i]
                    if i + 1 < len(pieces) and "(" in pieces[i + 1]:
                        rebuilt.append(cur + ", " + pieces[i + 1])
                        i += 2
                    else:
                        rebuilt.append(cur)
                        i += 1
                extracted = rebuilt
        else:
            kept.append(line)

    if extracted:
        cv["skills"] = "\n".join([x for x in kept if x.strip()])
        cv["languages"] = "\n".join(extracted)

    return cv


def postprocess_cv(cv: dict, company: str, role: str) -> dict:
    if not isinstance(cv, dict):
        return cv

    exp_heading = "Experience"
    if company and role:
        exp_heading = f"{company} - {role}"
    elif role:
        exp_heading = role
    elif company:
        exp_heading = company

    proj_heading = "Selected Project"

    cv["experience"] = ensure_headed_multiblock(cv.get("experience", ""), exp_heading)
    cv["projects"] = ensure_headed_multiblock(cv.get("projects", ""), proj_heading)
    return split_languages_from_skills(cv)


def build_prompt(
    baseline_text: str,
    jd_text: str,
    company: str,
    role: str,
    archetype: str,
    tone: str,
    length: str,
    custom_notes: str
):
    system_rules = f"""
You are a professional CV tailoring engine.

Your task:
- Tailor the candidate's CV to the specific job description.
- Use ONLY information that appears in the baseline CV.
- Never invent employers, companies, degrees, dates, tools, achievements, certifications, responsibilities, or links.
- You may rewrite, reorder, compress, emphasize, and remove irrelevant material.
- Keep content specific, credible, and professional.
- Tone: {tone}
- Archetype: {archetype}
- Length target: {length}

Return ONLY valid JSON.
No markdown.
No code fences.
No commentary.

Required JSON shape:
{{
  "cv": {{
    "headline": "short tailored headline",
    "summary": "short professional summary paragraph",
    "experience": "plain text where EACH role starts with a heading line like Company - Role | Dates, followed by bullet lines starting with •",
    "skills": "plain text, grouped lines like Data & Programming: Python, SQL",
    "languages": "plain text listing languages and levels, one per line, like Arabic (Native)",
    "education": "plain text where the first line is the degree/institution heading and the next line can contain coursework/details",
    "projects": "plain text where EACH project starts with a heading line like Project Name | Tools | Year, followed by bullet lines starting with •"
  }},
  "cover_letter": {{
    "subject": "short subject",
    "body": "plain text cover letter body"
  }},
  "notes": {{
    "keywords_used": ["keyword1", "keyword2"],
    "changes_made": ["change 1", "change 2"],
    "warnings": ["warning 1"]
  }}
}}

The "cv" object must ALWAYS contain:
headline, summary, experience, skills, languages, education, projects

The "cover_letter" object must ALWAYS contain:
subject, body

The "notes" object must ALWAYS contain:
keywords_used, changes_made, warnings
"""

    user_input = f"""
BASELINE_CV:
{baseline_text}

JOB_DESCRIPTION:
{jd_text}

JOB_CONTEXT:
Company={company}
Role={role}

Important:
- Keep the CV strong and concise.
- "experience", "skills", "languages", "education", and "projects" must always be strings even if empty.
- Bullet lines should begin with the bullet character •
- Skills should be grouped clearly.
- Languages must be separate from skills.
- Put languages in the "languages" field only, one per line, e.g. Arabic (Native)
- For EXPERIENCE: each role MUST begin with a heading line that includes employer and role, optionally with dates.
- For PROJECTS: each project MUST begin with a heading line that includes the project name, optionally tools and year.
- Do NOT output only anonymous bullets for experience or projects.
- Use polished hiring-friendly language.

CUSTOM_NOTES_FROM_USER:
{custom_notes or "None"}
"""

    return system_rules.strip(), user_input.strip()


def build_hebrew_translation_prompt(cv_en: dict) -> tuple[str, str]:
    system_rules = """
You are a professional Hebrew CV translator for Israeli job applications.

Translate the English CV fields into natural, professional Hebrew.

Rules:
- Return ONLY valid JSON.
- No markdown.
- No code fences.
- Preserve the same JSON keys.
- Keep technologies and brand names in English when that is more natural, such as Python, SQL, Power BI, Git, Streamlit, Tableau.
- Do not invent content.
- The user's actual degree is Information Systems.
- In Hebrew, prefer: מערכות מידע
- Never rewrite Information Systems as Computer Science or מדעי המחשב.
- Never rewrite Information Systems as Software Engineering, Data Science, הנדסת תוכנה, or any other degree.
- If the source CV says Information Systems, the Hebrew result must say מערכות מידע or Information Systems, never מדעי המחשב.
- Keep the structure of headings and bullet blocks.
- Keep project names and company names sensible. You may transliterate or leave proper names in English if that reads better.
- Keep dates and date ranges readable.
- Languages should remain a simple one-per-line list in Hebrew.
- Experience and projects should remain headed multi-line blocks, followed by bullet lines.
"""

    user_input = f"""
Translate this CV JSON into Hebrew and keep the exact same keys:

{json.dumps(cv_en, ensure_ascii=False, indent=2)}
"""
    return system_rules.strip(), user_input.strip()


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
    if not isinstance(cv, dict):
        return cv

    replacements = {
        "מדעי המחשב": "מערכות מידע",
        "תואר במדעי המחשב": "תואר במערכות מידע",
        "בוגר במדעי המחשב": "בוגר במערכות מידע",
        "בוגרת במדעי המחשב": "בוגרת במערכות מידע",
        "תואר ראשון במדעי המחשב": "תואר ראשון במערכות מידע",
        "computer science": "information systems",
        "degree in computer science": "degree in information systems",
    }

    for key in ["headline", "summary", "experience", "skills", "languages", "education", "projects"]:
        val = str(cv.get(key, "") or "")
        for bad, good in replacements.items():
            import re
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


conn = get_conn()
init_db(conn)
df = fetch_jobs(conn)

if df.empty:
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

choices = [f'#{r.id} | {r.company} - {r.role}' for r in df.itertuples(index=False)]
pick = st.selectbox("Select job", choices)
job_id = int(pick.split("|")[0].strip().replace("#", ""))
job = get_job(conn, job_id) or {}

st.subheader("Your details (used in PDF header)")
c1, c2, c3 = st.columns(3)
with c1:
    name = st.text_input("Name", value=profile["name"])
    headline_override = st.text_input("Headline override (optional)", value=profile["headline"])
with c2:
    email = st.text_input("Email", value=profile["email"])
    phone = st.text_input("Phone", value=profile["phone"])
with c3:
    github = st.text_input("GitHub URL", value=profile["github_url"])
    linkedin = st.text_input("LinkedIn URL", value=profile["linkedin_url"])
    location = st.text_input("Location", value=(job.get("location") or profile["location"] or ""))

website = st.text_input("Website URL (optional)", value=profile["website_url"])

contacts = {
    "email": email.strip(),
    "phone": phone.strip(),
    "github_url": github.strip(),
    "linkedin_url": linkedin.strip(),
    "website_url": website.strip(),
    "location": location.strip(),
}

st.subheader("Inputs")
left, right = st.columns(2)

with left:
    company = st.text_input("Company", value=job.get("company") or "")
    role = st.text_input("Role title", value=job.get("role") or "")
    baseline_text = st.text_area("Baseline CV text", height=260, value=baseline_saved)

with right:
    jd_text = st.text_area("Job description", height=220, value=job.get("jd_text") or "")
    custom_notes = st.text_area(
        "Custom notes for AI",
        height=110,
        placeholder="Example: Focus on BI and dashboards, mention leadership, keep it concise, emphasize customer-facing work..."
    )

archetype = st.selectbox("Archetype", ["Data/BI", "Marketing Analyst", "Ops/Management", "Fraud/Risk", "Custom"])
tone = st.selectbox("Tone", ["Concise", "Impact-driven", "Technical", "Leadership"])
length = st.selectbox("Length", ["1 page", "2 pages"])
include_cover = st.checkbox("Generate cover letter", value=True)

generate = st.button("Generate English CV + Hebrew CV + Cover PDF", type="primary", disabled=(not api_key), width="stretch")

if generate:
    if not baseline_text.strip():
        st.error("Baseline CV text is empty.")
        st.stop()

    if not jd_text.strip():
        st.error("Job description is empty.")
        st.stop()

    baseline_text2 = clamp_text(baseline_text, 12000)
    jd_text2 = clamp_text(jd_text, 12000)

    system_rules, user_input = build_prompt(
        baseline_text=baseline_text2,
        jd_text=jd_text2,
        company=company,
        role=role,
        archetype=archetype,
        tone=tone,
        length=length,
        custom_notes=custom_notes.strip()
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

        raw = resp.choices[0].message.content
        data = extract_json_object(raw)
        cv_en, cover_en, notes = normalize_bundle(data, headline_override, include_cover)
        cv_en = postprocess_cv(cv_en, company, role)

    except Exception as e:
        st.error(f"English generation failed: {e}")
        st.stop()

    # Hebrew translation of CV only, not saved in DB
    try:
        he_sys, he_user = build_hebrew_translation_prompt(cv_en)
        he_resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": he_sys},
                {"role": "user", "content": he_user},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        cv_he = normalize_hebrew_cv(extract_json_object(he_resp.choices[0].message.content))
        cv_he = enforce_hebrew_degree_truth(cv_he)
    except Exception as e:
        st.error(f"Hebrew translation failed: {e}")
        st.stop()

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
        notes_json=json.dumps(notes, ensure_ascii=False),
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
        ("Technical Skills", cv_en.get("skills", ""), "text"),
        ("Languages", cv_en.get("languages", ""), "text"),
        ("Selected Projects", cv_en.get("projects", ""), "text"),
        ("Experience", cv_en.get("experience", ""), "text"),
        ("Education", cv_en.get("education", ""), "text"),
    ]

    sections_he = [
        ("Technical Skills", cv_he.get("skills", ""), "text"),
        ("Languages", cv_he.get("languages", ""), "text"),
        ("Selected Projects", cv_he.get("projects", ""), "text"),
        ("Experience", cv_he.get("experience", ""), "text"),
        ("Education", cv_he.get("education", ""), "text"),
    ]

    try:
        export_cv_pdf(
            path=cv_pdf_en,
            name=name,
            headline=headline_en,
            contacts=contacts,
            summary=cv_en.get("summary", ""),
            sections=sections_en,
        )

        export_cv_pdf_he(
            path=cv_pdf_he,
            name=name,
            headline=headline_he,
            contacts=contacts,
            summary=cv_he.get("summary", ""),
            sections=sections_he,
        )

        archived_cv_en = archive_copy(cv_pdf_en, "cv", version_id)
        archived_cv_he = archive_copy(cv_pdf_he, "cv", version_id)

        cover_pdf_path = None
        archived_cover_en = None
        if include_cover and (cover_en.get("body", "").strip() or cover_en.get("subject", "").strip()):
            export_cover_letter_pdf(
                path=cl_pdf_en,
                name=name,
                contacts=contacts,
                letter_text=cover_en.get("body", ""),
                headline=headline_en,
                date_str=str(date.today()),
            )
            cover_pdf_path = cl_pdf_en
            archived_cover_en = archive_copy(cl_pdf_en, "cover", version_id)

        update_cv_paths(conn, version_id, cv_pdf_path=cv_pdf_en, cover_pdf_path=cover_pdf_path)

    except Exception as e:
        st.error(f"PDF build failed: {e}")
        st.stop()

    st.success(f"Saved version #{version_id} for job #{job_id}, built English CV, Hebrew CV, and English cover letter files.")

    st.subheader("English CV Preview")
    st.markdown("**Headline**")
    st.write(cv_en.get("headline", ""))
    st.markdown("**Summary**")
    st.write(cv_en.get("summary", ""))
    st.markdown("**Experience**")
    st.write(cv_en.get("experience", ""))
    st.markdown("**Skills**")
    st.write(cv_en.get("skills", ""))
    st.markdown("**Languages**")
    st.write(cv_en.get("languages", ""))
    st.markdown("**Education**")
    st.write(cv_en.get("education", ""))
    st.markdown("**Projects**")
    st.write(cv_en.get("projects", ""))

    st.divider()
    st.subheader("Hebrew CV Preview")
    st.markdown("**כותרת**")
    st.write(cv_he.get("headline", ""))
    st.markdown("**תקציר**")
    st.write(cv_he.get("summary", ""))
    st.markdown("**ניסיון**")
    st.write(cv_he.get("experience", ""))
    st.markdown("**כישורים**")
    st.write(cv_he.get("skills", ""))
    st.markdown("**שפות**")
    st.write(cv_he.get("languages", ""))
    st.markdown("**השכלה**")
    st.write(cv_he.get("education", ""))
    st.markdown("**פרויקטים**")
    st.write(cv_he.get("projects", ""))

    if include_cover:
        st.divider()
        st.subheader("English Cover Letter Preview")
        st.markdown("**Subject**")
        st.write(cover_en.get("subject", ""))
        st.markdown("**Body**")
        st.write(cover_en.get("body", ""))

    st.divider()
    st.subheader("ATS keyword coverage")
    try:
        cv_text_for_ats = "\n".join([
            cv_en.get("summary", ""),
            cv_en.get("experience", ""),
            cv_en.get("skills", ""),
            cv_en.get("languages", ""),
            cv_en.get("projects", ""),
            cv_en.get("education", ""),
        ])
        score, hit, miss, keys = coverage(jd_text, cv_text_for_ats, k=25)
        st.metric("Coverage", f"{score:.1f}%")
        st.write("Matched keywords:", ", ".join(hit) or "-")
        st.write("Missing keywords:", ", ".join(miss) or "-")
    except Exception:
        st.write("ATS panel failed to compute.")

    st.divider()
    st.subheader("Files")
    st.write(f"English CV saved to: `{cv_pdf_en}`")
    st.write(f"Hebrew CV saved to: `{cv_pdf_he}`")
    if include_cover and os.path.exists(cl_pdf_en):
        st.write(f"English cover letter saved to: `{cl_pdf_en}`")

    col1, col2, col3 = st.columns(3)

    with col1:
        with open(cv_pdf_en, "rb") as f:
            st.download_button(
                "Download English CV PDF",
                f,
                file_name=os.path.basename(cv_pdf_en),
                mime="application/pdf",
                width="stretch",
                on_click="ignore",
            )

    with col2:
        with open(cv_pdf_he, "rb") as f:
            st.download_button(
                "Download Hebrew CV PDF",
                f,
                file_name=os.path.basename(cv_pdf_he),
                mime="application/pdf",
                width="stretch",
                on_click="ignore",
            )

    with col3:
        if include_cover and os.path.exists(cl_pdf_en):
            with open(cl_pdf_en, "rb") as f:
                st.download_button(
                    "Download English Cover PDF",
                    f,
                    file_name=os.path.basename(cl_pdf_en),
                    mime="application/pdf",
                    width="stretch",
                    on_click="ignore",
                )
        else:
            st.write("No cover letter file.")

    st.caption(f"Archived English CV: {archived_cv_en}")
    st.caption(f"Archived Hebrew CV: {archived_cv_he}")
    if include_cover and archived_cover_en:
        st.caption(f"Archived English cover: {archived_cover_en}")



