from pathlib import Path
import re

p = Path(r"jobtracker\pages\5_CV.py")
txt = p.read_text(encoding="utf-8-sig")

# Fix indentation around Education block and insert Languages cleanly
pattern = r'st\.subheader\("Education"\)\s*\n\s*edu\s*=\s*st\.text_area\("Education".*?\)'

m = re.search(pattern, txt, re.S)
if not m:
    raise SystemExit("Could not find Education block to repair.")

replacement = '''st.subheader("Education")
edu = st.text_area("Education", height=90, value="B.Sc. Information Systems")

st.subheader("Languages")
languages = st.text_area(
    "Languages",
    height=70,
    value="Arabic (Native), English (Fluent), Hebrew (Conversational)"
)
'''

txt = txt[:m.start()] + replacement + txt[m.end():]

# Ensure Languages exists in sections list
sections_pattern = r'("Education",\s*edu,\s*"text"\s*\))'
txt = re.sub(
    sections_pattern,
    r'\1,\n        ("Languages", languages, "text")',
    txt,
    count=1
)

p.write_text(txt, encoding="utf-8-sig")

print("OK: Fixed indentation and added Languages section.")
