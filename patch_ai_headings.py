from pathlib import Path
import re

p = Path(r"jobtracker\pages\7_AI_CV_Generator.py")
txt = p.read_text(encoding="utf-8-sig")

# 1) Strengthen JSON shape comments
txt = txt.replace(
'''    "experience": "plain text with bullet lines starting with •",
    "skills": "plain text, preferably grouped lines like Data & Programming: Python, SQL",
    "education": "plain text",
    "projects": "plain text with bullet lines starting with •"''',
'''    "experience": "plain text where EACH role starts with a heading line like Company - Role | Dates, followed by bullet lines starting with •",
    "skills": "plain text, preferably grouped lines like Data & Programming: Python, SQL",
    "education": "plain text where the first line is the degree/institution heading and the next line can contain coursework/details",
    "projects": "plain text where EACH project starts with a heading line like Project Name | Tools | Year, followed by bullet lines starting with •"'''
)

# 2) Strengthen prompt instructions
txt = txt.replace(
'''- Bullet lines should begin with the bullet character •
- Skills should be grouped clearly.
- Use polished hiring-friendly language.''',
'''- Bullet lines should begin with the bullet character •
- Skills should be grouped clearly.
- For EXPERIENCE: each role MUST begin with a heading line that includes employer and role, optionally with dates. Example:
  Super-Pharm, Kiryat Ata - Shift Lead & Service Representative | 2022-Present
  • Managed ...
  • Selected ...
- For PROJECTS: each project MUST begin with a heading line that includes the project name, optionally tools and year. Example:
  Smart Inventory & AI Analytics Platform | Python, Streamlit, SQLite | 2025
  • Built ...
  • Designed ...
- Do NOT output only anonymous bullets for experience or projects.
- Use polished hiring-friendly language.'''
)

# 3) Add fallback formatter helpers after normalize_bundle if not present
if "def ensure_headed_multiblock" not in txt:
    insert_after = '    return cv, cover, notes\n'
    helper = '''

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
        return "\\n".join(non_empty)

    bullets = []
    paras = []
    for line in non_empty:
        s = line.strip()
        if s.startswith("•") or s.startswith("-"):
            bullets.append("• " + s.lstrip("•- ").strip())
        else:
            paras.append(s)

    body = bullets if bullets else ["• " + x for x in paras]
    return fallback_heading + "\\n" + "\\n".join(body)


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
    return cv
'''
    if insert_after in txt:
        txt = txt.replace(insert_after, insert_after + helper)

# 4) Apply postprocess right after normalize_bundle call
txt = txt.replace(
'        cv, cover, notes = normalize_bundle(data, headline_override, include_cover)',
'        cv, cover, notes = normalize_bundle(data, headline_override, include_cover)\n        cv = postprocess_cv(cv, company, role)'
)

p.write_text(txt, encoding="utf-8-sig")
print("Patched AI generator to force headings for experience and projects.")
