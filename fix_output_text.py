from pathlib import Path

patched = []

for p in Path("jobtracker").rglob("*.py"):
    txt = p.read_text(encoding="utf-8-sig", errors="ignore")
    new = txt.replace("response.output_text", "response.choices[0].message.content")
    if new != txt:
        p.write_text(new, encoding="utf-8-sig")
        patched.append(str(p))

if not patched:
    raise SystemExit("No files contained response.output_text")

print("Patched files:")
for x in patched:
    print("-", x)
