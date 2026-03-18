from pathlib import Path
import re

# -------------------------
# Patch pdf_export.py
# -------------------------
pdf = Path(r"jobtracker\lib\pdf_export.py")
txt = pdf.read_text(encoding="utf-8-sig")

# Replace the contact rendering block anchored between "def plain(" and the HR line.
start = txt.find("    def plain(label, val):")
if start == -1:
    raise SystemExit("pdf_export.py: couldn't find 'def plain(label, val)' anchor. Patch aborted.")

hr_match = re.search(r"(?m)^\s*_hr\(c,\s*left,\s*right,\s*y\)\s*$", txt)
if not hr_match:
    raise SystemExit("pdf_export.py: couldn't find '_hr(c, left, right, y)' anchor. Patch aborted.")

end = hr_match.end()

replacement = r'''    def plain(label, val):
        nonlocal x, y
        if val is None or str(val).strip() == "":
            return
        t = f"{label}: {val}"
        c.setFont("Helvetica", 9.6)
        c.setFillColor(colors.black)
        c.drawString(x, y, t)
        x += c.stringWidth(t, "Helvetica", 9.6) + 14

    def link_only(label, url):
        nonlocal x, y
        if not url:
            return
        w = _draw_link(c, x, y, label, url, "Helvetica", 9.6)
        x += w + 14

    # --- Header line 1: Email (clickable), Phone, Location ---
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

    # --- Header line 2: GitHub, LinkedIn (clickable words only) ---
    y -= 11
    x = left
    link_only("GitHub", github_url)
    link_only("LinkedIn", linkedin_url)

    y -= 10
    _hr(c, left, right, y)
'''

txt2 = txt[:start] + replacement + txt[end:]
pdf.write_text(txt2, encoding="utf-8-sig")

# -------------------------
# Patch 5_CV.py
# -------------------------
cv = Path(r"jobtracker\pages\5_CV.py")
cvt = cv.read_text(encoding="utf-8-sig")

# Insert Languages UI right after the Skills input (anchor: st.subheader("Skills"))
skills_anchor = 'st.subheader("Skills")'
pos = cvt.find(skills_anchor)
if pos == -1:
    raise SystemExit('5_CV.py: could not find st.subheader("Skills"). Patch aborted.')

# Find end of the skills block by locating the next st.subheader after Skills
after_skills = cvt.find("st.subheader(", pos + len(skills_anchor))
# If Skills is last, insert near end (unlikely)
if after_skills == -1:
    after_skills = len(cvt)

# Only insert if not already present
if 'st.subheader("Languages")' not in cvt:
    insert_ui = '\n    st.subheader("Languages")\n    languages = st.text_area("Languages", height=70, value="Arabic (Native), English (Fluent), Hebrew (Conversational)")\n'
    cvt = cvt[:after_skills] + insert_ui + cvt[after_skills:]

# Ensure sections list contains Languages entry
# We'll add it after Education if Education exists, otherwise append at end of sections list.
if '("Languages", languages' not in cvt:
    # Find sections list
    m = re.search(r"(?ms)\bsections\s*=\s*\[\s*(.*?)\s*\]\s*", cvt)
    if not m:
        raise SystemExit("5_CV.py: couldn't find sections = [...] list. Patch aborted.")
    body = m.group(1)

    # Insert after Education if present
    if "Education" in body:
        body2 = re.sub(r'(\("Education"\s*,\s*[^)]+\)\s*,?)', r"\1\n            (\"Languages\", languages, \"text\"),", body, count=1)
    else:
        body2 = body.rstrip() + '\n            ("Languages", languages, "text"),\n'

    cvt = cvt[:m.start(1)] + body2 + cvt[m.end(1):]

cv.write_text(cvt, encoding="utf-8-sig")

print("OK: patched pdf_export.py header + added Languages to 5_CV.py.")
