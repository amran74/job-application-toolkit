from pathlib import Path
from datetime import datetime

p = Path(r"jobtracker\pages\7_AI_CV_Generator.py")
txt = p.read_text(encoding="utf-8-sig")

bak = p.with_name(p.name + ".bak_indentfix_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
bak.write_text(txt, encoding="utf-8-sig")

old = '''    if isinstance(data, dict):
    cv = data.get("cv") or data.get("resume") or data.get("content") or {}
else:
    cv = data

if isinstance(cv, str):
    cv = {
        "headline": headline_override or "",
        "summary": cv,
        "sections": []
    }

if not isinstance(cv, dict):
'''

new = '''    if isinstance(data, dict):
        cv = data.get("cv") or data.get("resume") or data.get("content") or {}
        cover = data.get("cover", {})
    else:
        cv = data
        cover = {}

    if isinstance(cv, str):
        cv = {
            "headline": headline_override or "",
            "summary": cv,
            "sections": []
        }

    if not isinstance(cv, dict):
        cv = {
            "headline": headline_override or "",
            "summary": str(cv),
            "sections": []
        }

    if not isinstance(cover, dict):
        cover = {"body": str(cover)}
'''

if old not in txt:
    raise SystemExit("Expected broken block not found exactly. Aborting.")

txt = txt.replace(old, new)

# clean up any leftover old cover assignment if present later
txt = txt.replace('cover = data.get("cover", {}) if isinstance(data, dict) else {}\nif not isinstance(cover, dict):\n    cover = {"body": str(cover)}', '')

# safe key access everywhere
txt = txt.replace('headline = cv["headline"]', 'headline = cv.get("headline", headline_override or "")')
txt = txt.replace('summary = cv["summary"]', 'summary = cv.get("summary", "")')
txt = txt.replace('sections = cv["sections"]', 'sections = cv.get("sections", [])')
txt = txt.replace('cover["body"]', 'cover.get("body", "")')
txt = txt.replace('cover["subject"]', 'cover.get("subject", "")')

p.write_text(txt, encoding="utf-8-sig")

print("Fixed indentation and CV parsing block.")
print("Backup:", bak.name)
