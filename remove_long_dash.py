from pathlib import Path

p = Path(r"jobtracker\lib\pdf_export.py")
txt = p.read_text(encoding="utf-8-sig")

txt = txt.replace(" — ", ", ")
txt = txt.replace('replace(" (", " — ").replace(")", "")', 'replace(" (", ", ").replace(")", "")')

p.write_text(txt, encoding="utf-8-sig")
print("Removed long dash formatting.")
