from pathlib import Path
import re

p = Path(r"jobtracker\pages\5_CV.py")
txt = p.read_text(encoding="utf-8-sig")

# Replace the existing Languages textarea block with a structured "Add language" UI.
# We match:
#   st.subheader("Languages")
#   languages = st.text_area(...)
pat = r'(?ms)^\s*st\.subheader\("Languages"\)\s*\n\s*languages\s*=\s*st\.text_area\("Languages".*?\)\s*\n'
m = re.search(pat, txt)
if not m:
    raise SystemExit('Could not find the Languages textarea block to replace (st.subheader("Languages") + languages = st.text_area).')

replacement = r'''st.subheader("Languages")

# Structured Languages (like Certificates): add language + pick level
# Defaults: Arabic (Native), English (Fluent), Hebrew (Fluent)
if "languages_items" not in st.session_state:
    st.session_state.languages_items = [
        {"language": "Arabic", "level": "Native"},
        {"language": "English", "level": "Fluent"},
        {"language": "Hebrew", "level": "Fluent"},
    ]

LEVELS = ["Native", "Fluent", "Professional", "Conversational", "Basic"]

to_delete = None
for i, item in enumerate(st.session_state.languages_items):
    cols = st.columns([3, 2, 1])
    item["language"] = cols[0].text_input("Language", value=item.get("language", ""), key=f"lang_name_{i}")
    item["level"] = cols[1].selectbox("Level", LEVELS, index=LEVELS.index(item.get("level", "Fluent")) if item.get("level") in LEVELS else 1, key=f"lang_level_{i}")
    if cols[2].button("🗑️", key=f"lang_del_{i}"):
        to_delete = i

if to_delete is not None:
    st.session_state.languages_items.pop(to_delete)
    st.rerun()

if st.button("➕ Add language"):
    st.session_state.languages_items.append({"language": "", "level": "Fluent"})
    st.rerun()

# Build export string for PDF (bullets)
languages = "\n".join(
    f"- {x['language'].strip()} ({x['level']})"
    for x in st.session_state.languages_items
    if x.get("language") and x["language"].strip()
)
'''

txt2 = txt[:m.start()] + replacement + txt[m.end():]
p.write_text(txt2, encoding="utf-8-sig")
print("OK: Languages textarea replaced with structured Add Language + Level UI.")
