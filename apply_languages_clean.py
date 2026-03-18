from pathlib import Path
import re

p = Path(r"jobtracker\pages\5_CV.py")
txt = p.read_text(encoding="utf-8-sig")

# Insert Languages UI right after Skills textarea assignment (works even if your file structure varies)
# We look for the first occurrence of: skills = st.text_area("Skills", ...)
m = re.search(r'(?ms)^\s*skills\s*=\s*st\.text_area\("Skills".*?\)\s*$', txt)
if not m:
    raise SystemExit("Could not find the Skills textarea assignment (skills = st.text_area(...)).")

insert = '\n\nst.subheader("Languages")\nlanguages = st.text_area("Languages", height=70, value="Arabic (Native), English (Fluent), Hebrew (Conversational)")\n'
if 'st.subheader("Languages")' not in txt:
    txt = txt[:m.end()] + insert + txt[m.end():]

# Add Languages to the sections list.
# Find sections = [ .... ] and append an entry at the end (before closing ])
sec = re.search(r'(?ms)^\s*sections\s*=\s*\[\s*(.*?)\s*\]\s*$', txt)
if not sec:
    # If sections list isn't a single block, try a broader match
    sec = re.search(r'(?ms)\bsections\s*=\s*\[\s*(.*?)\s*\]\s*', txt)
    if not sec:
        raise SystemExit("Could not find sections = [...] list.")

body = sec.group(1)

# Prevent duplicates
if '("Languages"' not in body:
    # Try to insert after Education if present, else append
    if '("Education"' in body:
        body2 = body.replace('("Education"', '("Education"', 1)
        # Insert after the first Education tuple line end
        body2 = re.sub(r'(\("Education".*?\)\s*,?)', r'\1\n        ("Languages", languages, "text"),', body, count=1, flags=re.S)
    else:
        body2 = body.rstrip() + '\n        ("Languages", languages, "text"),\n'
    txt = txt[:sec.start(1)] + body2 + txt[sec.end(1):]

p.write_text(txt, encoding="utf-8-sig")
print("OK: Languages added cleanly.")
