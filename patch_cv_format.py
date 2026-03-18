import re
from pathlib import Path

# ---------------------------
# Patch 1: lib/pdf_export.py
# ---------------------------
pdf_path = Path(r"jobtracker\lib\pdf_export.py")
txt = pdf_path.read_text(encoding="utf-8-sig")

# Replace the whole contacts block (x=left .. before the HR line) with a cleaner 2-line header:
# Line 1: Email + Phone + Location
# Line 2: GitHub + LinkedIn (clickable, no prefixes)
contacts_pat = r"""(?ms)
    x\s*=\s*left\s*\n
    .*?
    y\s*-\=\s*10\s*\n
    _hr\(c,\s*left,\s*right,\s*y\)\s*\n
"""
m = re.search(contacts_pat, txt)
if not m:
    raise SystemExit("pdf_export.py patch failed: couldn't locate contacts header block.")

replacement_contacts = r'''    x = left

    def plain(label, val):
        nonlocal x, y
        txt = f"{label}: {val}"
        c.setFont("Helvetica", 9.6)
        c.setFillColor(colors.black)
        c.drawString(x, y, txt)
        x += c.stringWidth(txt, "Helvetica", 9.6) + 14

    def link_only(label, url):
        nonlocal x, y
        if not url:
            return
        wlink = _draw_link(c, x, y, label, url, "Helvetica", 9.6)
        x += wlink + 14

    # --- Line 1: Email / Phone / Location ---
    if email:
        prefix = "Email: "
        c.setFont("Helvetica", 9.6)
        c.setFillColor(colors.black)
        c.drawString(x, y, prefix)
        x += c.stringWidth(prefix, "Helvetica", 9.6)
        w = _draw_link(c, x, y, email, f"mailto:{email}", "Helvetica", 9.6)
        x += w + 14

    if phone:
        plain("Phone", phone)

    if location:
        plain("Location", location)

    # --- Line 2: GitHub / LinkedIn (no prefixes, just clickable words) ---
    y -= 11
    x = left

    if github_url:
        link_only("GitHub", github_url)

    if linkedin_url:
        link_only("LinkedIn", linkedin_url)

    y -= 10
    _hr(c, left, right, y)
'''

txt = txt[:m.start()] + replacement_contacts + "\n" + txt[m.end():]
pdf_path.write_text(txt, encoding="utf-8-sig")

# Also: make Skills/Languages use bullet separators automatically (keeps layout intact)
txt = pdf_path.read_text(encoding="utf-8-sig")

# Find the section loop and inject a tiny normalization before rendering
# We look for: for title, body, kind in sections:
loop_pat = r'(?m)^ {4}for title, body, kind in sections:\n'
if re.search(loop_pat, txt):
    if "if title in (\"Skills\", \"Languages\")" not in txt:
        txt = re.sub(
            loop_pat,
            '    for title, body, kind in sections:\n'
            '        # Clean formatting for Skills/Languages without changing layout\n'
            '        if kind == "text" and title in ("Skills", "Languages"):\n'
            '            body = (body or "").replace(" ,", ",").replace(", ", " • ").replace(",", " • ")\n',
            txt,
            count=1
        )
        pdf_path.write_text(txt, encoding="utf-8-sig")
else:
    raise SystemExit("pdf_export.py patch failed: section loop not found.")

# ---------------------------
# Patch 2: pages/5_CV.py
# ---------------------------
cv_path = Path(r"jobtracker\pages\5_CV.py")
cv = cv_path.read_text(encoding="utf-8-sig")

# Add Languages UI after Education block
# We locate the Education input and insert a Languages block right after it.
edu_block_pat = r'(st\.subheader\("Education"\)\s*\n\s*edu\s*=\s*st\.text_area\("Education".*?\)\s*\n)'
m = re.search(edu_block_pat, cv, flags=re.S)
if not m:
    raise SystemExit("5_CV.py patch failed: couldn't find the Education block.")

insert_languages_ui = m.group(1) + '\n    st.subheader("Languages")\n    languages = st.text_area("Languages", height=70, value="Arabic (Native), English (Fluent), Hebrew (Conversational)")\n'
cv = cv[:m.start()] + insert_languages_ui + cv[m.end():]

# Reorder sections list + add Languages at the end
# Replace the sections = [...] block exactly
sections_pat = r'(?ms)\s*sections\s*=\s*\[\s*.*?\s*\]\s*\n\s*export_cv_pdf\('
m = re.search(sections_pat, cv)
if not m:
    raise SystemExit("5_CV.py patch failed: couldn't find sections list block.")

new_sections_block = '''
        sections = [
            ("Experience", exp, "bullets"),
            ("Projects", projects_bullets, "bullets_links"),
            ("Skills", skills, "text"),
            ("Certificates", certs_bullets, "bullets_links"),
            ("Education", edu, "text"),
            ("Languages", languages, "text"),
        ]

        export_cv_pdf(
'''
cv = cv[:m.start()] + new_sections_block + cv[m.end():]

cv_path.write_text(cv, encoding="utf-8-sig")

print("OK: Patched pdf_export.py + 5_CV.py (header improved, Skills moved, Languages added).")
