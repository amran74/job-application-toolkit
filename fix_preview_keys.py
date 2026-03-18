from pathlib import Path
from datetime import datetime

p = Path(r"jobtracker\pages\7_AI_CV_Generator.py")
txt = p.read_text(encoding="utf-8-sig")

bak = p.with_name(p.name + ".bak_previewfix_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
bak.write_text(txt, encoding="utf-8-sig")

replacements = {
    'st.markdown("**Headline**"); st.write(cv["headline"])':
        'st.markdown("**Headline**"); st.write(cv.get("headline", headline_override or ""))',

    'st.markdown("**Summary**"); st.write(cv["summary"])':
        'st.markdown("**Summary**"); st.write(cv.get("summary", ""))',

    'for sec in cv["sections"]:':
        'for sec in cv.get("sections", []):',

    'st.write(cover["body"])':
        'st.write(cover.get("body", ""))',

    'st.write(cover["subject"])':
        'st.write(cover.get("subject", ""))',
}

for old, new in replacements.items():
    txt = txt.replace(old, new)

# extra safety for alternate quote/layout variants
txt = txt.replace('cv["headline"]', 'cv.get("headline", headline_override or "")')
txt = txt.replace('cv["summary"]', 'cv.get("summary", "")')
txt = txt.replace('cv["sections"]', 'cv.get("sections", [])')
txt = txt.replace('cover["body"]', 'cover.get("body", "")')
txt = txt.replace('cover["subject"]', 'cover.get("subject", "")')

p.write_text(txt, encoding="utf-8-sig")

print("Patched preview accessors to use safe .get(...) lookups.")
print("Backup:", bak.name)
