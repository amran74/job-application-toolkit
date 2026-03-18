from pathlib import Path
import re

p = Path(r"jobtracker\pages\5_CV.py")
txt = p.read_text(encoding="utf-8-sig")

# Find the skills textarea line to anchor insertion
m = re.search(r'(?m)^(?P<indent>\s*)skills\s*=\s*st\.text_area\("Skills".*', txt)
if not m:
    raise SystemExit("Could not find Skills textarea assignment (skills = st.text_area(...)).")

indent = m.group("indent")

# Insert languages UI right after the skills textarea block (until next st.subheader)
# We'll insert immediately after the first occurrence of the skills line (safe & minimal)
if 'st.subheader("Languages")' not in txt:
    insert = (
        "\n"
        f"{indent}st.subheader(\"Languages\")\n"
        f"{indent}languages = st.text_area(\"Languages\", height=70, "
        f"value=\"Arabic (Native), English (Fluent), Hebrew (Conversational)\")\n"
    )
    # Insert after the skills line (not perfect, but safe and won't break indentation)
    lines = txt.splitlines(True)
    out = []
    inserted = False
    for line in lines:
        out.append(line)
        if (not inserted) and re.match(rf'^{re.escape(indent)}skills\s*=\s*st\.text_area\("Skills"', line):
            out.append(insert)
            inserted = True
    txt = "".join(out)

# Add Languages to sections list (detect list indentation too)
sec = re.search(r'(?ms)^(?P<indent>\s*)sections\s*=\s*\[(?P<body>.*?)^\s*\]\s*', txt)
if not sec:
    raise SystemExit("Could not find sections = [...] block.")

sec_indent = sec.group("indent")
body = sec.group("body")

if '("Languages"' not in body:
    # append right before closing bracket, keep same indent level as other tuples
    # detect tuple indent from first tuple line
    t = re.search(r'(?m)^(?P<tindent>\s*)\("', body)
    tindent = t.group("tindent") if t else (sec_indent + "    ")
    body = body.rstrip() + f'\n{tindent}("Languages", languages, "text"),\n'
    txt = txt[:sec.start("body")] + body + txt[sec.end("body"):]

p.write_text(txt, encoding="utf-8-sig")
print("OK: Languages added without breaking indentation.")
