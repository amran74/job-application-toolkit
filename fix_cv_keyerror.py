from pathlib import Path
from datetime import datetime
import re

p = Path(r"jobtracker\pages\7_AI_CV_Generator.py")
txt = p.read_text(encoding="utf-8-sig")

bak = p.with_name(p.name + ".bak_cvkey_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
bak.write_text(txt, encoding="utf-8-sig")

old = '''cv = data["cv"]
cover = data.get("cover", {})
'''

new = '''# tolerate both old JSON responses and new plain-text responses
if isinstance(data, dict):
    cv = data.get("cv", data.get("resume", data.get("content", {})))
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

if old in txt:
    txt = txt.replace(old, new)
else:
    # fallback: replace only the exploding line + nearby cover line
    txt = re.sub(
        r'cv\s*=\s*data\["cv"\]\s*\n\s*cover\s*=\s*data\.get\("cover",\s*\{\}\)\s*',
        new,
        txt,
        count=1
    )

# also make sure missing keys later don't explode
txt = txt.replace('headline = cv["headline"]', 'headline = cv.get("headline", headline_override or "")')
txt = txt.replace('summary = cv["summary"]', 'summary = cv.get("summary", "")')
txt = txt.replace('sections = cv["sections"]', 'sections = cv.get("sections", [])')
txt = txt.replace('cover["body"]', 'cover.get("body", "")')
txt = txt.replace('cover["subject"]', 'cover.get("subject", "")')

p.write_text(txt, encoding="utf-8-sig")

print("Patched 7_AI_CV_Generator.py to handle plain-text or JSON AI output.")
print("Backup:", bak.name)
