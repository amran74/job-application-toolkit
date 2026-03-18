import re
from pathlib import Path

p = Path(r"jobtracker\lib\pdf_export.py")
txt = p.read_text(encoding="utf-8-sig")

if "def export_cover_letter_pdf" in txt:
    print("OK: export_cover_letter_pdf already exists. No changes made.")
    raise SystemExit(0)

# Append a minimal cover letter PDF exporter
add = r'''

def export_cover_letter_pdf(path, name, contacts, letter_text, headline="", date_str=""):
    """
    Minimal cover letter PDF generator.
    Keeps same style system as CV exporter, but simpler.
    contacts keys supported: email, phone, location, github_url, linkedin_url
    """
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    left = 2.0 * cm
    right = w - 2.0 * cm
    y = h - 2.0 * cm

    # Header
    c.setFont("Helvetica-Bold", 20)
    c.drawString(left, y, _safe(name))
    y -= 16

    if headline:
        c.setFont("Helvetica", 11)
        c.drawString(left, y, _safe(headline))
        y -= 12

    email = _safe((contacts or {}).get("email"))
    phone = _safe((contacts or {}).get("phone"))
    github_url = _normalize_url((contacts or {}).get("github_url"))
    linkedin_url = _normalize_url((contacts or {}).get("linkedin_url"))
    location = _safe((contacts or {}).get("location"))

    x = left

    def plain(label, val):
        nonlocal x, y
        if not val:
            return
        txt2 = f"{label}: {val}"
        c.setFont("Helvetica", 9.6)
        c.drawString(x, y, txt2)
        x += c.stringWidth(txt2, "Helvetica", 9.6) + 14

    def link_only(label, url):
        nonlocal x, y
        if not url:
            return
        wlink = _draw_link(c, x, y, label, url, "Helvetica", 9.6)
        x += wlink + 14

    # Contact line 1
    if email:
        prefix = "Email: "
        c.setFont("Helvetica", 9.6)
        c.drawString(x, y, prefix)
        x += c.stringWidth(prefix, "Helvetica", 9.6)
        wmail = _draw_link(c, x, y, email, f"mailto:{email}", "Helvetica", 9.6)
        x += wmail + 14

    plain("Phone", phone)
    plain("Location", location)

    # Contact line 2 (links only)
    if github_url or linkedin_url:
        y -= 11
        x = left
        link_only("GitHub", github_url)
        link_only("LinkedIn", linkedin_url)

    y -= 10
    _hr(c, left, right, y)
    y -= 14

    # Optional date line
    if date_str:
        c.setFont("Helvetica", 10)
        c.drawString(left, y, _safe(date_str))
        y -= 14

    # Body (supports paragraphs separated by blank lines)
    body = (letter_text or "").strip()
    if body:
        for para in body.split("\n\n"):
            para = para.strip()
            if not para:
                continue
            y = _draw_wrapped(c, left, y, para, max_chars=105, line_h=12, font="Helvetica", size=10)
            y -= 10

    c.save()
'''

# Ensure file ends with newline then append
if not txt.endswith("\n"):
    txt += "\n"
txt2 = txt + add

p.write_text(txt2, encoding="utf-8-sig")
print("OK: Added export_cover_letter_pdf to lib/pdf_export.py")
