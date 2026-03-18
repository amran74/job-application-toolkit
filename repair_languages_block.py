from pathlib import Path
import re
from datetime import datetime

p = Path(r"jobtracker\lib\pdf_export.py")
txt = p.read_text(encoding="utf-8-sig")

bak = p.with_name(p.name + ".fixlang_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
bak.write_text(txt, encoding="utf-8-sig")

# Replace the whole broken Languages block inside the section loop
patterns = [
    r'''if kind == "text" and title == "Languages":.*?if title != sections\[0\]\[0\]:''',
    r'''if kind == "text" and title == "Languages":.*?y -= 6''',
]

replacement = '''if kind == "text" and title == "Languages":
            b = (body or "").strip()
            if "\\n" not in b and " - " in b:
                parts = [x.strip(" -") for x in b.split(" - ") if x.strip(" -")]
                body = "\\n".join(f"- {x}" for x in parts)
            body = body.replace(" (", ", ").replace(")", "")

        if title != sections[0][0]:'''

done = False
for pat in patterns:
    new_txt = re.sub(pat, replacement, txt, count=1, flags=re.S)
    if new_txt != txt:
        txt = new_txt
        done = True
        break

if not done:
    # fallback: directly fix the exact mangled junk if present
    txt = txt.replace('if "\n', 'if "\\n" not in b and " - " in b:\n')
    txt = txt.replace('" not in b and " - " in b:', '"\\n" not in b and " - " in b:')
    txt = txt.replace(" — ", ", ")

p.write_text(txt, encoding="utf-8-sig")
print("Repaired Languages block.")
print("Backup:", bak.name)
