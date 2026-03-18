from pathlib import Path
from datetime import datetime

p = Path(r"jobtracker\pages\7_AI_CV_Generator.py")
txt = p.read_text(encoding="utf-8-sig")

bak = p.with_name(p.name + ".bak_previewkeys_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
bak.write_text(txt, encoding="utf-8-sig")

# brute-force convert remaining direct key access to safe lookups
txt = txt.replace('cv["headline"]', 'cv.get("headline", headline_override or "")')
txt = txt.replace('cv["summary"]', 'cv.get("summary", "")')
txt = txt.replace('cv["experience"]', 'cv.get("experience", "")')
txt = txt.replace('cv["skills"]', 'cv.get("skills", "")')
txt = txt.replace('cv["projects"]', 'cv.get("projects", "")')
txt = txt.replace('cv["education"]', 'cv.get("education", "")')
txt = txt.replace('cv["languages"]', 'cv.get("languages", "")')
txt = txt.replace('cv["sections"]', 'cv.get("sections", [])')

txt = txt.replace('cover["body"]', 'cover.get("body", "")')
txt = txt.replace('cover["subject"]', 'cover.get("subject", "")')

txt = txt.replace('notes["ats_keywords"]', 'notes.get("ats_keywords", "")')
txt = txt.replace('notes["missing_keywords"]', 'notes.get("missing_keywords", "")')
txt = txt.replace('notes["suggestions"]', 'notes.get("suggestions", "")')

p.write_text(txt, encoding="utf-8-sig")

print("Patched remaining preview key access.")
print("Backup:", bak.name)
