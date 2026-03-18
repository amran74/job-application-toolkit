import re
from pathlib import Path

p = Path(r"jobtracker\lib\pdf_export.py")
txt = p.read_text(encoding="utf-8-sig")

# -----------------------------
# 1) Fix header: add GitHub/LinkedIn line back + keep clean contact line
# Replace the block that ends with: _hr(c, left, right, y)
# -----------------------------
header_pat = r"(?ms)^\s*# --- Header line 1:.*?^\s*_hr\(c,\s*left,\s*right,\s*y\)\s*$"
m = re.search(header_pat, txt)
if not m:
    # fallback: replace between 'def plain' and the _hr(...) line (safer if comments differ)
    start = txt.find("    def plain(label, val):")
    hr = re.search(r"(?m)^\s*_hr\(c,\s*left,\s*right,\s*y\)\s*$", txt)
    if start == -1 or not hr:
        raise SystemExit("Could not locate header block anchors in pdf_export.py")
    # keep the helper defs, replace everything after helpers up to hr
    # find end of helpers by locating the first blank line after link_only definition
    # but simplest: replace from 'x = left' before Email block if exists; else from start
    # We'll replace from first 'x = left' after helpers:
    xmatch = re.search(r"(?m)^\s*x\s*=\s*left\s*$", txt[start:hr.start()])
    if not xmatch:
        raise SystemExit("Header patch failed: couldn't find 'x = left' in header area.")
    hs = start + xmatch.start()
    he = hr.end()
    new_header = '''    x = left

    # --- Header line 1: Email (clickable), Phone, Location ---
    if email:
        prefix = "Email: "
        c.setFont("Helvetica", 9.6)
        c.setFillColor(colors.black)
        c.drawString(x, y, prefix)
        x += c.stringWidth(prefix, "Helvetica", 9.6)
        w = _draw_link(c, x, y, email, f"mailto:{email}", "Helvetica", 9.6)
        x += w + 14

    plain("Phone", phone)
    plain("Location", location)

    # --- Header line 2: GitHub + LinkedIn (clickable words only) ---
    y -= 11
    x = left
    if github_url:
        link_only("GitHub", github_url)
    if linkedin_url:
        link_only("LinkedIn", linkedin_url)

    y -= 10
    _hr(c, left, right, y)
'''
    txt = txt[:hs] + new_header + txt[he:]
else:
    # if the comment-based block exists, replace it entirely with the same content
    new_header_block = '''    # --- Header line 1: Email (clickable), Phone, Location ---
    x = left

    if email:
        prefix = "Email: "
        c.setFont("Helvetica", 9.6)
        c.setFillColor(colors.black)
        c.drawString(x, y, prefix)
        x += c.stringWidth(prefix, "Helvetica", 9.6)
        w = _draw_link(c, x, y, email, f"mailto:{email}", "Helvetica", 9.6)
        x += w + 14

    plain("Phone", phone)
    plain("Location", location)

    # --- Header line 2: GitHub + LinkedIn (clickable words only) ---
    y -= 11
    x = left
    if github_url:
        link_only("GitHub", github_url)
    if linkedin_url:
        link_only("LinkedIn", linkedin_url)

    y -= 10
    _hr(c, left, right, y)
'''
    txt = txt[:m.start()] + new_header_block + txt[m.end():]

# -----------------------------
# 2) Improve spacing + formatting in the section rendering loop
# - add extra spacing between sections
# - make Skills pretty (• separators)
# - make Languages one-per-line
# -----------------------------
loop_pat = r'(?m)^\s*for\s+title,\s*body,\s*kind\s+in\s+sections\s*:\s*$'
m = re.search(loop_pat, txt)
if not m:
    raise SystemExit("Could not find: for title, body, kind in sections:  (layout patch aborted)")

inject = '''
        # --- Layout polish: spacing + formatting ---
        body = body or ""

        # Skills: commas -> bullets on one line
        if kind == "text" and title == "Skills":
            body = body.replace(" ,", ",").replace(", ", " • ").replace(",", " • ")

        # Languages: convert single-line dash-separated to separate lines
        if kind == "text" and title == "Languages":
            b = body.strip()
            if "\\n" not in b and " - " in b:
                parts = [x.strip(" -") for x in b.split(" - ") if x.strip(" -")]
                body = "\\n".join(f"- {x}" for x in parts)
            # Convert "(Level)" to "— Level" look (optional polish)
            body = body.replace(" (", " — ").replace(")", "")

        # Extra breathing room between sections (except first)
        if title != sections[0][0]:
            y -= 6
'''

# Inject only once (avoid duplicates)
if "Layout polish: spacing + formatting" not in txt:
    txt = re.sub(loop_pat, lambda mm: mm.group(0) + inject, txt, count=1)

p.write_text(txt, encoding="utf-8-sig")
print("OK: pdf_export.py patched (header links + spacing + Skills/Languages formatting).")
