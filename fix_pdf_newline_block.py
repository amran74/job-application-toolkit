from pathlib import Path
from datetime import datetime

p = Path(r"jobtracker\lib\pdf_export.py")
txt = p.read_text(encoding="utf-8-sig")

bak = p.with_name(p.name + ".fixnewline_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
bak.write_text(txt, encoding="utf-8-sig")

old = '''        # Languages: convert single-line dash-separated to separate lines
        if kind == "text" and title == "Languages":
            b = (body or "").strip()
            if "
" not in b and " - " in b:
                parts = [x.strip(" -") for x in b.split(" - ") if x.strip(" -")]
                body = "
".join(f"- {x}" for x in parts)
            body = body.replace(" (", ", ").replace(")", "")
'''

new = '''        # Languages: convert single-line dash-separated to separate lines
        if kind == "text" and title == "Languages":
            b = (body or "").strip()
            if "\\n" not in b and " - " in b:
                parts = [x.strip(" -") for x in b.split(" - ") if x.strip(" -")]
                body = "\\n".join(f"- {x}" for x in parts)
            body = body.replace(" (", ", ").replace(")", "")
'''

if old not in txt:
    raise SystemExit("Expected broken Languages block not found exactly. Aborting so we don't damage the file further.")

txt = txt.replace(old, new)
p.write_text(txt, encoding="utf-8-sig")

print("Fixed broken newline literals in pdf_export.py")
print("Backup:", bak.name)
