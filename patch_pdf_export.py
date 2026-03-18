import re
from pathlib import Path

p = Path(r"jobtracker\lib\pdf_export.py")
txt = p.read_text(encoding="utf-8-sig")

# Find the link_label function defined INSIDE export_cv_pdf (indented 4 spaces)
m = re.search(r"(?ms)^( {4})def link_label\(label, url\):\n(.*?)(?=^ {4}\S)", txt)
if not m:
    raise SystemExit("Could not find indented link_label(label, url) block to patch.")

indent = m.group(1)

new_block = (
    f"{indent}def link_label(label, url):\n"
    f"{indent}    nonlocal x, y\n"
    f"{indent}    if not url:\n"
    f"{indent}        return\n"
    f"{indent}    # GitHub/LinkedIn: show ONLY clickable text (no 'Label: ' prefix)\n"
    f"{indent}    wlink = _draw_link(c, x, y, label, url, \"Helvetica\", 9.6)\n"
    f"{indent}    x += wlink + 14\n"
)

txt2 = txt[:m.start()] + new_block + txt[m.end():]
p.write_text(txt2, encoding="utf-8-sig")

# Print the patched function so you can VERIFY it
m2 = re.search(r"(?ms)^( {4})def link_label\(label, url\):\n(.*?)(?=^ {4}\S)", txt2)
print("PATCHED:\n" + txt2[m2.start():m2.end()])
