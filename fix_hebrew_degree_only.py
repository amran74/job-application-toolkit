from pathlib import Path

p = Path(r"jobtracker\pages\7_AI_CV_Generator.py")
txt = p.read_text(encoding="utf-8-sig")

old_prompt = """- Do not invent content.
- If the English CV says Information Systems, keep it as Information Systems / מערכות מידע as appropriate. Never translate or rewrite it as Computer Science / מדעי המחשב unless the source explicitly says that."""
new_prompt = """- Do not invent content.
- The user's actual degree is Information Systems.
- In Hebrew, prefer: מערכות מידע
- Never rewrite Information Systems as Computer Science or מדעי המחשב.
- Never rewrite Information Systems as Software Engineering, Data Science, הנדסת תוכנה, or any other degree.
- If the source CV says Information Systems, the Hebrew result must say מערכות מידע or Information Systems, never מדעי המחשב."""

if old_prompt in txt:
    txt = txt.replace(old_prompt, new_prompt)
else:
    txt = txt.replace("- Do not invent content.", new_prompt)

helper = '''

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

'''

if 'def enforce_hebrew_degree_truth(cv: dict) -> dict:' not in txt:
    marker = 'def archive_copy(src_path: str, kind: str, version_id: int):'
    if marker not in txt:
        raise SystemExit("Could not find insertion point for Hebrew degree helper.")
    txt = txt.replace(marker, helper + "\n" + marker)

old_line = '        cv_he = normalize_hebrew_cv(extract_json_object(he_resp.choices[0].message.content))'
new_line = '''        cv_he = normalize_hebrew_cv(extract_json_object(he_resp.choices[0].message.content))
        cv_he = enforce_hebrew_degree_truth(cv_he)'''

if old_line not in txt:
    raise SystemExit("Could not find Hebrew normalization line to patch.")
txt = txt.replace(old_line, new_line)

p.write_text(txt, encoding="utf-8-sig")
print("Patched Hebrew degree correction successfully.")
