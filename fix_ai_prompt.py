from pathlib import Path
import re

root = Path("jobtracker")

target = None
for p in root.rglob("*.py"):
    txt = p.read_text(encoding="utf-8", errors="ignore")
    if "chat.completions.create" in txt:
        target = p
        break

if not target:
    raise SystemExit("Could not find AI generation file")

txt = target.read_text(encoding="utf-8", errors="ignore")

# replace any broken call using undefined prompt variable
txt = re.sub(
    r'client\.chat\.completions\.create\([\s\S]*?\)',
'''client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a professional resume writer."},
            {"role": "user", "content": user_input}
        ],
        temperature=0.4
    )''',
txt
)

# ensure response parsing is correct
txt = txt.replace(
    "response.output_text",
    "response.choices[0].message.content"
)

target.write_text(txt, encoding="utf-8")

print("AI generator repaired in:", target)
