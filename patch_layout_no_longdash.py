from pathlib import Path
import re
from datetime import datetime

p = Path(r"jobtracker\lib\pdf_export.py")
txt = p.read_text(encoding="utf-8-sig")

bak = p.with_name(p.name + ".bak_layout_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
bak.write_text(txt, encoding="utf-8-sig")

# 1) Remove ugly long dash formatting logic if it exists
txt = txt.replace('body = body.replace(" (", " — ").replace(")", "")', 'body = body.replace(" (", ", ").replace(")", "")')

# 2) If old language formatter exists, replace it with comma based formatting
txt = re.sub(
    r'''if kind == "text" and title == "Languages":\s*
\s*b = body\.strip\(\)\s*
\s*if "\\n" not in b and " - " in b:\s*
\s*parts = \[x\.strip\(" -"\) for x in b\.split\(" - "\) if x\.strip\(" -"\)\]\s*
\s*body = "\\n"\.join\(f"- \{x\}" for x in parts\)\s*
\s*# Convert .*?\n\s*body = .*?\n''',
    '''if kind == "text" and title == "Languages":
            b = body.strip()
            if "\\n" not in b and " - " in b:
                parts = [x.strip(" -") for x in b.split(" - ") if x.strip(" -")]
                body = "\\n".join(f"- {x}" for x in parts)
            body = body.replace(" (", ", ").replace(")", "")
''',
    txt,
    flags=re.S
)

# 3) Add cleaner section spacing if not already present
if 'SECTION_SPACING = 8' not in txt:
    txt = txt.replace('LINK_BLUE = colors.HexColor("#0563C1")', 'LINK_BLUE = colors.HexColor("#0563C1")\nSECTION_SPACING = 8\nLINE_SPACING = 12')

# 4) Tighten header spacing a bit
txt = txt.replace('y -= 11', 'y -= 10')
txt = txt.replace('y -= 10\n    _hr(c, left, right, y)', 'y -= 8\n    _hr(c, left, right, y)')

# 5) Improve section spacing inside the sections loop
loop_pat = r'(?m)^(\s*)for\s+title,\s*body,\s*kind\s+in\s+sections\s*:\s*$'
m = re.search(loop_pat, txt)
if m and 'SECTION_SPACING' in txt and 'Extra breathing room between sections' not in txt:
    indent = m.group(1)
    inject = f'''
{indent}for title, body, kind in sections:
{indent}    body = body or ""
{indent}
{indent}    if kind == "text" and title == "Skills":
{indent}        body = body.replace(" ,", ",").replace(", ", " • ").replace(",", " • ")
{indent}
{indent}    if kind == "text" and title == "Languages":
{indent}        body = body.replace(" (", ", ").replace(")", "")
{indent}
{indent}    y -= SECTION_SPACING
'''
    txt = re.sub(loop_pat, inject.rstrip(), txt, count=1)

# 6) Force any accidental long dash in file to comma-space
txt = txt.replace(" — ", ", ")

p.write_text(txt, encoding="utf-8-sig")
print("OK: layout cleaned, long dash removed, Languages now use commas.")
print(f"Backup created: {bak.name}")
