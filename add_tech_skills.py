import re
from pathlib import Path

p = Path(r"jobtracker\pages\5_CV.py")
txt = p.read_text(encoding="utf-8-sig")

# -----------------------------
# 1) Insert Technical Skills UI
# Place it right after Projects block (before the next section header)
# -----------------------------
proj = re.search(r'(?m)^(?P<indent>\s*)st\.subheader\("Projects"\)\s*$', txt)
if not proj:
    raise SystemExit('Could not find st.subheader("Projects") in 5_CV.py')

indent = proj.group("indent")

# Find the next st.subheader after Projects (insert before it)
next_hdr = re.search(r'(?m)^\s*st\.subheader\("(?!Projects")', txt[proj.end():])
insert_pos = proj.end() + (next_hdr.start() if next_hdr else len(txt) - proj.end())

if 'st.subheader("Technical Skills")' not in txt:
    block = f'''

{indent}st.subheader("Technical Skills")
{indent}tech_skills = st.text_area(
{indent}    "Technical Skills",
{indent}    height=140,
{indent}    value="Programming: Python, SQL\\nBI & Visualization: Power BI, Streamlit\\nData Engineering: ETL\\nData Analysis: Analytics, Dashboarding\\nTools: Git, Excel, SQLite"
{indent})
'''
    txt = txt[:insert_pos] + block + txt[insert_pos:]

# -----------------------------
# 2) Add Technical Skills into sections list (right after Projects)
# -----------------------------
sec = re.search(r'(?ms)\bsections\s*=\s*\[(?P<body>.*?)\]\s*', txt)
if not sec:
    raise SystemExit("Could not find sections = [...] list in 5_CV.py")

body = sec.group("body")

if '("Technical Skills"' not in body:
    # Insert after Projects tuple if it exists
    if '("Projects"' in body:
        body2 = re.sub(
            r'(\("Projects".*?\)\s*,?)',
            r'\1\n        ("Technical Skills", tech_skills, "text"),',
            body,
            count=1,
            flags=re.S
        )
    else:
        # If Projects tuple isn't found (weird), append near end
        body2 = body.rstrip() + '\n        ("Technical Skills", tech_skills, "text"),\n'
    txt = txt[:sec.start("body")] + body2 + txt[sec.end("body"):]

p.write_text(txt, encoding="utf-8-sig")
print("OK: Added Technical Skills UI + inserted it into sections list.")
