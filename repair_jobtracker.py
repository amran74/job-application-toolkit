from pathlib import Path
import re
from datetime import datetime

ROOT = Path(".")
FILES = {
    "db": ROOT / "jobtracker" / "lib" / "db.py",
    "pdf": ROOT / "jobtracker" / "lib" / "pdf_export.py",
    "ai": ROOT / "jobtracker" / "pages" / "7_AI_CV_Generator.py",
    "profile": ROOT / "jobtracker" / "pages" / "10_Profile_Settings.py",
    "cvlib": ROOT / "jobtracker" / "pages" / "14_CV_Library.py",
}

ts = datetime.now().strftime("%Y%m%d_%H%M%S")
for p in FILES.values():
    if p.exists():
        p.with_name(p.name + f".repairbak_{ts}").write_text(p.read_text(encoding="utf-8-sig"), encoding="utf-8-sig")

def read(p: Path) -> str:
    return p.read_text(encoding="utf-8-sig")

def write(p: Path, txt: str):
    p.write_text(txt, encoding="utf-8-sig")

# -------------------------------------------------
# 1) db.py - centralize cv_library schema
# -------------------------------------------------
p = FILES["db"]
txt = read(p)

if "CREATE TABLE IF NOT EXISTS cv_library" not in txt:
    m = re.search(r'conn\.commit\(\)', txt)
    if m:
        block = '''
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cv_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            label TEXT NOT NULL,
            source TEXT NOT NULL,
            job_id INTEGER,
            file_path TEXT NOT NULL,
            notes TEXT
        );
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cv_library_job ON cv_library(job_id);")

'''
        txt = txt[:m.start()] + block + txt[m.start():]
write(p, txt)

# -------------------------------------------------
# 2) 14_CV_Library.py - remove page-owned schema
# -------------------------------------------------
p = FILES["cvlib"]
txt = read(p)
txt = re.sub(
    r'(?s)\n# --- Create library table .*?conn\.commit\(\)\n',
    '\n',
    txt
)
write(p, txt)

# -------------------------------------------------
# 3) 10_Profile_Settings.py - add Website URL field + saving
# -------------------------------------------------
p = FILES["profile"]
txt = read(p)

if 'profile_website_url' not in txt:
    txt = re.sub(
        r'(with c2:\s*\n(?:.*\n)*?\s*linkedin_url\s*=\s*field\("profile_linkedin_url",\s*"LinkedIn URL"\)\s*\n)',
        r'\1\nwebsite_url = field("profile_website_url", "Website URL")\n',
        txt,
        count=1
    )

    txt = re.sub(
        r'(\s*set_setting\(conn,\s*"profile_linkedin_url",\s*linkedin_url\.strip\(\)\)\s*\n)',
        r'\1    set_setting(conn, "profile_website_url", website_url.strip())\n',
        txt,
        count=1
    )

write(p, txt)

# -------------------------------------------------
# 4) pdf_export.py - make sure cover exporter exists
#    and add website_url support where possible
# -------------------------------------------------
p = FILES["pdf"]
txt = read(p)

# Add website_url extraction in export_cv_pdf if possible
if 'website_url = _normalize_url(contacts.get("website_url"))' not in txt:
    txt = re.sub(
        r'(github_url\s*=\s*_normalize_url\(contacts\.get\("github_url"\)\)\s*\n\s*linkedin_url\s*=\s*_normalize_url\(contacts\.get\("linkedin_url"\)\)\s*\n)',
        r'\1    website_url = _normalize_url(contacts.get("website_url"))\n',
        txt,
        count=1
    )

# Add Website link to CV header if link_label exists
if 'link_label("Website", website_url)' not in txt:
    txt = re.sub(
        r'(link_label\("LinkedIn",\s*linkedin_url\)\s*\n)',
        r'\1    link_label("Website", website_url)\n',
        txt,
        count=1
    )

# Add website_url extraction in cover exporter block if exporter already exists
if 'def export_cover_letter_pdf' in txt and 'website_url = _normalize_url((contacts or {}).get("website_url"))' not in txt:
    txt = re.sub(
        r'(github_url\s*=\s*_normalize_url\(\(contacts or \{\}\)\.get\("github_url"\)\)\s*\n\s*linkedin_url\s*=\s*_normalize_url\(\(contacts or \{\}\)\.get\("linkedin_url"\)\)\s*\n)',
        r'\1    website_url = _normalize_url((contacts or {}).get("website_url"))\n',
        txt,
        count=1
    )
    txt = re.sub(
        r'(link_only\("LinkedIn",\s*linkedin_url\)\s*\n)',
        r'\1        link_only("Website", website_url)\n',
        txt,
        count=1
    )

# Ensure docstring mentions website_url if present
txt = txt.replace(
    'contacts keys supported: email, phone, location, github_url, linkedin_url',
    'contacts keys supported: email, phone, location, github_url, linkedin_url, website_url'
)

# Append minimal cover exporter if missing
if "def export_cover_letter_pdf" not in txt:
    add = '''

def export_cover_letter_pdf(path, name, contacts, letter_text, headline="", date_str=""):
    """
    Minimal cover letter PDF generator.
    contacts keys supported: email, phone, location, github_url, linkedin_url, website_url
    """
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    left = 2.0 * cm
    right = w - 2.0 * cm
    y = h - 2.0 * cm

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
    website_url = _normalize_url((contacts or {}).get("website_url"))
    location = _safe((contacts or {}).get("location"))

    x = left

    def plain(label, val):
        nonlocal x, y
        if not val:
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
        w2 = _draw_link(c, x, y, label, url, "Helvetica", 9.6)
        x += w2 + 14

    if email:
        prefix = "Email: "
        c.setFont("Helvetica", 9.6)
        c.setFillColor(colors.black)
        c.drawString(x, y, prefix)
        x += c.stringWidth(prefix, "Helvetica", 9.6)
        wmail = _draw_link(c, x, y, email, f"mailto:{email}", "Helvetica", 9.6)
        x += wmail + 14

    plain("Phone", phone)
    plain("Location", location)

    if github_url or linkedin_url or website_url:
        y -= 11
        x = left
        link_only("GitHub", github_url)
        link_only("LinkedIn", linkedin_url)
        link_only("Website", website_url)

    y -= 10
    _hr(c, left, right, y)
    y -= 14

    if date_str:
        c.setFont("Helvetica", 10)
        c.drawString(left, y, _safe(date_str))
        y -= 14

    body = (letter_text or "").strip()
    if body:
        for para in body.split("\\n\\n"):
            para = para.strip()
            if not para:
                continue
            y = _draw_wrapped(c, left, y, para, max_chars=105, line_h=12, font="Helvetica", size=10)
            y -= 10

    c.save()
'''
    if not txt.endswith("\n"):
        txt += "\n"
    txt += add

write(p, txt)

# -------------------------------------------------
# 5) 7_AI_CV_Generator.py - normalize profile + contacts + cover call
# -------------------------------------------------
p = FILES["ai"]
txt = read(p)

# Inject profile dict after baseline_saved
if 'profile = {' not in txt:
    txt = re.sub(
        r'(baseline_saved\s*=\s*get_setting\(conn,\s*"baseline_cv_text"\)\s*\n)',
        r'''\1
profile = {
    "name": get_setting(conn, "profile_name") or "Amran",
    "headline": get_setting(conn, "profile_headline") or "",
    "email": get_setting(conn, "profile_email") or "",
    "phone": get_setting(conn, "profile_phone") or "",
    "github_url": get_setting(conn, "profile_github_url") or "",
    "linkedin_url": get_setting(conn, "profile_linkedin_url") or "",
    "website_url": get_setting(conn, "profile_website_url") or "",
    "location": get_setting(conn, "profile_location") or "",
}
''',
        txt,
        count=1
    )

# Replace hardcoded empty profile inputs
txt = txt.replace('name = st.text_input("Name", value="Amran")', 'name = st.text_input("Name", value=profile["name"])')
txt = txt.replace('headline_override = st.text_input("Headline override (optional)", value="")', 'headline_override = st.text_input("Headline override (optional)", value=profile["headline"])')
txt = txt.replace('email = st.text_input("Email", value="")', 'email = st.text_input("Email", value=profile["email"])')
txt = txt.replace('phone = st.text_input("Phone", value="")', 'phone = st.text_input("Phone", value=profile["phone"])')
txt = txt.replace('github = st.text_input("GitHub (username or URL)", value="")', 'github = st.text_input("GitHub (username or URL)", value=profile["github_url"])')
txt = txt.replace('linkedin = st.text_input("LinkedIn (handle or URL)", value="")', 'linkedin = st.text_input("LinkedIn (handle or URL)", value=profile["linkedin_url"])')
txt = txt.replace('website = st.text_input("Website (optional)", value="")', 'website = st.text_input("Website (optional)", value=profile["website_url"])')
txt = txt.replace('location = st.text_input("Location", value=(job.get("location") or ""))', 'location = st.text_input("Location", value=(job.get("location") or profile["location"] or ""))')

# Fix contacts dict keys
txt = re.sub(
    r'contacts\s*=\s*\{[^\}]*"email"\s*:\s*email[^\}]*"phone"\s*:\s*phone[^\}]*"github"\s*:\s*github[^\}]*"linkedin"\s*:\s*linkedin[^\}]*"website"\s*:\s*website[^\}]*"location"\s*:\s*location[^\}]*\}',
    '''contacts = {
    "email": email.strip(),
    "phone": phone.strip(),
    "github_url": github.strip(),
    "linkedin_url": linkedin.strip(),
    "website_url": website.strip(),
    "location": location.strip(),
}''',
    txt,
    count=1,
    flags=re.S
)

# Fix cover exporter call
txt = re.sub(
    r'export_cover_letter_pdf\(\s*path=cl_pdf,\s*name=name,\s*contacts=contacts,\s*subject=cover\["subject"\],\s*body=cover\["body"\],\s*\)',
    '''export_cover_letter_pdf(
                path=cl_pdf,
                name=name,
                contacts=contacts,
                letter_text=cover["body"],
                headline=headline,
                date_str=str(date.today()),
            )''',
    txt,
    count=1,
    flags=re.S
)

write(p, txt)

print("Repair completed.")
for k, p in FILES.items():
    print(f"- patched: {p}")
print(f"- backups suffix: .repairbak_{ts}")
