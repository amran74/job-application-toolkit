import re
from pathlib import Path

p = Path(r"jobtracker\pages\5_CV.py")
txt = p.read_text(encoding="utf-8-sig")

# 1) Find Skills anchor (we insert Languages right after it)
m = re.search(r'(?m)^(?P<indent>\s*)st\.subheader\("Skills"\)\s*$', txt)
if not m:
    raise SystemExit('Could not find st.subheader("Skills") in 5_CV.py')

indent = m.group("indent")

# Find where Skills block ends = next st.subheader(...) after Skills
m2 = re.search(r'(?m)^\s*st\.subheader\("(?!Skills")', txt[m.end():])
insert_pos = m.end() + (m2.start() if m2 else len(txt) - m.end())

# 2) Insert Languages UI if missing
if 'st.subheader("Languages")' not in txt:
    block = f'''

{indent}st.subheader("Languages")

{indent}# Structured Languages: Add language + choose level
{indent}# Defaults: Arabic (Native), English (Fluent), Hebrew (Fluent)
{indent}if "languages_items" not in st.session_state:
{indent}    st.session_state.languages_items = [
{indent}        {{"language": "Arabic", "level": "Native"}},
{indent}        {{"language": "English", "level": "Fluent"}},
{indent}        {{"language": "Hebrew", "level": "Fluent"}},
{indent}    ]

{indent}LEVELS = ["Native", "Fluent", "Professional", "Conversational", "Basic"]

{indent}to_delete = None
{indent}for i, item in enumerate(st.session_state.languages_items):
{indent}    cols = st.columns([3, 2, 1])
{indent}    item["language"] = cols[0].text_input("Language", value=item.get("language", ""), key=f"lang_name_{{i}}")
{indent}    lvl = item.get("level", "Fluent")
{indent}    idx = LEVELS.index(lvl) if lvl in LEVELS else 1
{indent}    item["level"] = cols[1].selectbox("Level", LEVELS, index=idx, key=f"lang_level_{{i}}")
{indent}    if cols[2].button("🗑️", key=f"lang_del_{{i}}"):
{indent}        to_delete = i

{indent}if to_delete is not None:
{indent}    st.session_state.languages_items.pop(to_delete)
{indent}    st.rerun()

{indent}if st.button("➕ Add language"):
{indent}    st.session_state.languages_items.append({{"language": "", "level": "Fluent"}})
{indent}    st.rerun()

{indent}# Build export string for PDF (bullets)
{indent}languages = "\\n".join(
{indent}    f"- {{x['language'].strip()}} ({{x['level']}})"
{indent}    for x in st.session_state.languages_items
{indent}    if x.get("language") and x["language"].strip()
{indent})
'''
    txt = txt[:insert_pos] + block + txt[insert_pos:]

# 3) Ensure Languages is in sections list
sec = re.search(r'(?ms)\bsections\s*=\s*\[(?P<body>.*?)\]\s*', txt)
if not sec:
    raise SystemExit("Could not find sections = [...] in 5_CV.py")

body = sec.group("body")
if '("Languages"' not in body:
    # Insert after Education if present, else append
    if '("Education"' in body:
        body2 = re.sub(r'(\("Education".*?\)\s*,?)', r'\1\n        ("Languages", languages, "text"),', body, count=1, flags=re.S)
    else:
        body2 = body.rstrip() + '\n        ("Languages", languages, "text"),\n'
    txt = txt[:sec.start("body")] + body2 + txt[sec.end("body"):]

p.write_text(txt, encoding="utf-8-sig")
print("OK: Inserted structured Languages section + added it to sections list.")
