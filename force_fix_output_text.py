from pathlib import Path

patched = []
hits = []

for p in Path("jobtracker").rglob("*.py"):
    txt = p.read_text(encoding="utf-8-sig", errors="ignore")
    original = txt

    if ".output_text" in txt:
        txt = txt.replace(".output_text", ".choices[0].message.content")

    if txt != original:
        p.write_text(txt, encoding="utf-8-sig")
        patched.append(str(p))

for p in Path("jobtracker").rglob("*.py"):
    txt = p.read_text(encoding="utf-8-sig", errors="ignore")
    for i, line in enumerate(txt.splitlines(), start=1):
        if any(x in line for x in [
            "output_text",
            "chat.completions.create",
            "responses.create",
            "choices[0].message.content",
            "OpenAI(",
            "from openai import"
        ]):
            hits.append(f"{p}:{i}: {line}")

print("PATCHED FILES:")
for x in patched:
    print(x)

print("\nOPENAI-RELATED LINES:")
for x in hits:
    print(x)
