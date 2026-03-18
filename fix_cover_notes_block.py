from pathlib import Path
from datetime import datetime

p = Path(r"jobtracker\pages\7_AI_CV_Generator.py")
txt = p.read_text(encoding="utf-8-sig")

bak = p.with_name(p.name + ".bak_coverfix_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
bak.write_text(txt, encoding="utf-8-sig")

old = '''    if not isinstance(cover, dict):
        cover = {"body": str(cover)}
    cv = {
        "headline": headline_override or "",
        "summary": str(cv),
        "sections": []
    }
    cover = data["cover_letter"]
    notes = data["notes"]
'''

new = '''    if not isinstance(cover, dict):
        cover = {"body": str(cover)}

    notes = data.get("notes", {}) if isinstance(data, dict) else {}

    if include_cover:
        if isinstance(data, dict):
            cover = data.get("cover_letter") or data.get("cover") or cover
        else:
            cover = cover or {}
    else:
        cover = {}
'''

if old not in txt:
    raise SystemExit("Expected broken cover/notes block not found exactly. Aborting.")

txt = txt.replace(old, new)

# extra safety for any remaining direct indexing
txt = txt.replace('cover = data["cover_letter"]', 'cover = data.get("cover_letter", data.get("cover", {})) if isinstance(data, dict) else {}')
txt = txt.replace('notes = data["notes"]', 'notes = data.get("notes", {}) if isinstance(data, dict) else {}')

p.write_text(txt, encoding="utf-8-sig")

print("Fixed cover_letter / notes handling.")
print("Backup:", bak.name)
