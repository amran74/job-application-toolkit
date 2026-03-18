from pathlib import Path
import re

targets = [
    Path(r"jobtracker\pages\7_AI_CV_Generator.py"),
    Path(r"jobtracker\lib\ai_tools.py"),
]

found = None
for p in targets:
    if p.exists():
        txt = p.read_text(encoding="utf-8-sig")
        if "responses.create(" in txt or "text.format" in txt:
            found = p
            break

if not found:
    # broader search
    for p in Path("jobtracker").rglob("*.py"):
        txt = p.read_text(encoding="utf-8-sig")
        if "responses.create(" in txt or "text.format" in txt:
            found = p
            break

if not found:
    raise SystemExit("Could not find the broken OpenAI request in jobtracker/*.py")

txt = found.read_text(encoding="utf-8-sig")
bak = found.with_name(found.name + ".bak_api_fix")
bak.write_text(txt, encoding="utf-8-sig")

# replace Responses API call with stable Chat Completions call
txt = re.sub(
    r'client\.responses\.create\((.*?)\)',
    '''client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a professional resume writer. Return only the requested resume content in clean plain text."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4
    )''',
    txt,
    flags=re.S
)

# fix response access
txt = txt.replace("response.output_text", "response.choices[0].message.content")

# remove likely broken structured-output fragments if still present
txt = re.sub(r'text\s*=\s*\{.*?\}\s*,?', '', txt, flags=re.S)
txt = re.sub(r'text_format\s*=\s*\{.*?\}\s*,?', '', txt, flags=re.S)

found.write_text(txt, encoding="utf-8-sig")
print(f"Patched file: {found}")
print(f"Backup: {bak}")
