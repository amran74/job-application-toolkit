from pathlib import Path
from datetime import datetime

p = Path(r"jobtracker\pages\7_AI_CV_Generator.py")
txt = p.read_text(encoding="utf-8-sig")

bak = p.with_name(p.name + ".bak_forcefix_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
bak.write_text(txt, encoding="utf-8-sig")

# brute-force replacements for the broken assumptions
txt = txt.replace('cv = data["cv"]', '''if isinstance(data, dict):
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
    cv = {
        "headline": headline_override or "",
        "summary": str(cv),
        "sections": []
    }''')

txt = txt.replace('cover = data.get("cover", {})', '''cover = data.get("cover", {}) if isinstance(data, dict) else {}
if not isinstance(cover, dict):
    cover = {"body": str(cover)}''')

txt = txt.replace('headline = cv["headline"]', 'headline = cv.get("headline", headline_override or "")')
txt = txt.replace('summary = cv["summary"]', 'summary = cv.get("summary", "")')
txt = txt.replace('sections = cv["sections"]', 'sections = cv.get("sections", [])')
txt = txt.replace('cover["body"]', 'cover.get("body", "")')
txt = txt.replace('cover["subject"]', 'cover.get("subject", "")')

p.write_text(txt, encoding="utf-8-sig")

print("Force-fixed 7_AI_CV_Generator.py")
print("Backup:", bak.name)
