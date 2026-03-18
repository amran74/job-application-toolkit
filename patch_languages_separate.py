from pathlib import Path

p = Path(r"jobtracker\pages\7_AI_CV_Generator.py")
txt = p.read_text(encoding="utf-8-sig")

# 1) Add languages to JSON shape in prompt
txt = txt.replace(
    '"skills": "plain text, preferably grouped lines like Data & Programming: Python, SQL",\n    "education": "plain text where the first line is the degree/institution heading and the next line can contain coursework/details",',
    '"skills": "plain text, preferably grouped lines like Data & Programming: Python, SQL",\n    "languages": "plain text listing languages and levels, one per line, like Arabic (Native)",\n    "education": "plain text where the first line is the degree/institution heading and the next line can contain coursework/details",'
)

# 2) Add languages to required fields text
txt = txt.replace(
    'headline, summary, experience, skills, education, projects',
    'headline, summary, experience, skills, languages, education, projects'
)

# 3) Add languages instruction to user prompt
txt = txt.replace(
    '- Skills should be grouped clearly.\n- Use polished hiring-friendly language.',
    '- Skills should be grouped clearly.\n- Languages must be separate from skills.\n- Put languages in the "languages" field only, one per line, e.g. Arabic (Native)\n- Use polished hiring-friendly language.'
)

# 4) Normalize bundle: include languages
txt = txt.replace(
    '"skills": "",\n            "education": "",',
    '"skills": "",\n            "languages": "",\n            "education": "",'
)

txt = txt.replace(
    '"skills": str(cv.get("skills", "") or ""),\n        "education": str(cv.get("education", "") or ""),',
    '"skills": str(cv.get("skills", "") or ""),\n        "languages": str(cv.get("languages", "") or ""),\n        "education": str(cv.get("education", "") or ""),'
)

# 5) Preview section
txt = txt.replace(
    '    st.markdown("**Skills**")\n    st.write(cv.get("skills", ""))\n\n    st.markdown("**Education**")',
    '    st.markdown("**Skills**")\n    st.write(cv.get("skills", ""))\n\n    st.markdown("**Languages**")\n    st.write(cv.get("languages", ""))\n\n    st.markdown("**Education**")'
)

# 6) ATS text includes languages if present
txt = txt.replace(
    '            cv.get("skills", ""),\n            cv.get("projects", ""),',
    '            cv.get("skills", ""),\n            cv.get("languages", ""),\n            cv.get("projects", ""),'
)

# 7) Export sections: split languages from technical skills
txt = txt.replace(
    '    sections = [\n        ("Technical Skills", cv.get("skills", ""), "text"),\n        ("Selected Projects", cv.get("projects", ""), "text"),\n        ("Experience", cv.get("experience", ""), "text"),\n        ("Education", cv.get("education", ""), "text"),\n    ]',
    '    sections = [\n        ("Technical Skills", cv.get("skills", ""), "text"),\n        ("Languages", cv.get("languages", ""), "text"),\n        ("Selected Projects", cv.get("projects", ""), "text"),\n        ("Experience", cv.get("experience", ""), "text"),\n        ("Education", cv.get("education", ""), "text"),\n    ]'
)

# 8) If model leaves languages inside skills, extract a simple fallback
needle = '    return cv, cover, notes\n'
helper = '''

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
            parts = [x.strip() for x in rhs.split(",") if x.strip()]
            # regroup pairs like Arabic (Native), English (Fluent)
            if rhs:
                extracted.append(rhs)
        else:
            kept.append(line)

    if extracted:
        cv["skills"] = "\\n".join([x for x in kept if x.strip()])
        cv["languages"] = "\\n".join(extracted)

    return cv
'''
if helper not in txt and needle in txt:
    txt = txt.replace(needle, needle + helper)

# 9) Call fallback after postprocess_cv
txt = txt.replace(
    '        cv = postprocess_cv(cv, company, role)',
    '        cv = postprocess_cv(cv, company, role)\n        cv = split_languages_from_skills(cv)'
)

p.write_text(txt, encoding="utf-8-sig")
print("Patched AI generator: Languages now separate from Technical Skills.")
