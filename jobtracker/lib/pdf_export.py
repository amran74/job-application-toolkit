from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import re

try:
    from bidi.algorithm import get_display as bidi_get_display
except Exception:
    bidi_get_display = None

PAGE_W, PAGE_H = A4
LEFT = 2.05 * cm
RIGHT = PAGE_W - 2.05 * cm
TOP = PAGE_H - 1.75 * cm
BOTTOM = 1.7 * cm

NAME_COLOR = colors.black
TEXT_COLOR = colors.HexColor("#30343A")
MUTED_COLOR = colors.HexColor("#6A7A8C")
SECTION_COLOR = colors.HexColor("#587087")
RULE_COLOR = colors.HexColor("#B5C0CB")
LINK_COLOR = colors.HexColor("#245E8A")

NAME_SIZE = 26
HEADLINE_SIZE = 11.8
CONTACT_SIZE = 9.9
SECTION_SIZE = 12.9
BODY_SIZE = 10.7
HEADING_SIZE = 11.2

HEADER_GAP_AFTER_NAME = 20
HEADER_GAP_AFTER_HEADLINE = 16
HEADER_GAP_AFTER_CONTACTS = 14
SECTION_TOP_GAP = 10
SECTION_RULE_GAP = 12
SECTION_BODY_GAP = 16
PARA_LINE_GAP = 14
BULLET_LINE_GAP = 14
ENTRY_HEADING_GAP = 10
SECTION_BOTTOM_GAP = 8

HEBREW_FONT_NAME = "HebrewCVFont"


def _safe(v):
    return ("" if v is None else str(v)).strip()


def _normalize_url(url):
    url = _safe(url)
    if not url:
        return ""
    if url.startswith(("http://", "https://", "mailto:")):
        return url
    if "linkedin.com" in url or "github.com" in url:
        return "https://" + url
    if "@" in url and " " not in url and "." in url:
        return "mailto:" + url
    return "https://" + url


def _set(c, font="Helvetica", size=10, color=TEXT_COLOR):
    c.setFont(font, size)
    c.setFillColor(color)


def _hr(c, y):
    c.setStrokeColor(RULE_COLOR)
    c.setLineWidth(0.75)
    c.line(LEFT, y, RIGHT, y)


def _string_width(c, text, font="Helvetica", size=10):
    return c.stringWidth(_safe(text), font, size)


def _draw_link(c, x, y, label, url, font="Helvetica", size=9.6):
    label = _safe(label)
    url = _normalize_url(url)
    if not label or not url:
        return 0
    _set(c, font, size, LINK_COLOR)
    c.drawString(x, y, label)
    w = c.stringWidth(label, font, size)
    c.linkURL(url, (x, y - 2, x + w, y + size + 2), relative=0)
    return w


def _wrap(text, font="Helvetica", size=10, width=RIGHT - LEFT, c=None):
    text = _safe(text)
    if not text:
        return []

    words = text.split()
    if not words:
        return []

    lines = []
    current = words[0]

    for word in words[1:]:
        test = current + " " + word
        w = _string_width(c, test, font, size) if c else len(test) * size * 0.45
        if w <= width:
            current = test
        else:
            lines.append(current)
            current = word

    lines.append(current)
    return lines


def _ensure_space(c, y, needed):
    if y - needed < BOTTOM:
        c.showPage()
        return TOP
    return y


def _draw_centered(c, y, text, font="Helvetica", size=10, color=TEXT_COLOR):
    text = _safe(text)
    if not text:
        return y
    _set(c, font, size, color)
    w = c.stringWidth(text, font, size)
    c.drawString((PAGE_W - w) / 2.0, y, text)
    return y


def _draw_paragraph(c, y, text, font="Helvetica", size=BODY_SIZE, color=TEXT_COLOR, line_gap=PARA_LINE_GAP):
    lines = _wrap(text, font=font, size=size, width=RIGHT - LEFT, c=c)
    if not lines:
        return y
    y = _ensure_space(c, y, len(lines) * line_gap + 6)
    _set(c, font, size, color)
    for line in lines:
        c.drawString(LEFT, y, line)
        y -= line_gap
    return y


def _draw_bullet(c, y, text, bullet="•", size=BODY_SIZE):
    text = _safe(text)
    if not text:
        return y

    m = re.search(r'https?://\S+', text)
    if m:
        url = m.group(0)
        label = "Project link"
        y = _ensure_space(c, y, BULLET_LINE_GAP + 4)
        _set(c, "Helvetica", size, TEXT_COLOR)
        c.drawString(LEFT, y, bullet)
        _draw_link(c, LEFT + 14, y, label, url, "Helvetica", size)
        return y - BULLET_LINE_GAP

    lines = _wrap(text, font="Helvetica", size=size, width=(RIGHT - LEFT - 18), c=c)
    if not lines:
        return y

    y = _ensure_space(c, y, len(lines) * BULLET_LINE_GAP + 4)
    _set(c, "Helvetica", size, TEXT_COLOR)
    c.drawString(LEFT, y, bullet)
    c.drawString(LEFT + 14, y, lines[0])

    for line in lines[1:]:
        y -= BULLET_LINE_GAP
        c.drawString(LEFT + 14, y, line)

    return y - BULLET_LINE_GAP


def _draw_section_title(c, y, title):
    y -= SECTION_TOP_GAP
    y = _ensure_space(c, y, 34)
    _set(c, "Helvetica-Bold", SECTION_SIZE, SECTION_COLOR)
    c.drawString(LEFT, y, _safe(title))
    y -= SECTION_RULE_GAP
    _hr(c, y)
    return y - SECTION_BODY_GAP


def _split_heading_date(text):
    text = _safe(text)
    if not text:
        return "", ""

    m = re.match(r"^(.*?)(?:\s{2,}| \| |\s+-\s+)(\d{4}(?:\s*-\s*(?:Present|\d{4}))?|Present|\d{4}\s*to\s*Present)$", text, flags=re.I)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    m = re.match(r"^(.*?)(\b(?:19|20)\d{2}\s*-\s*(?:Present|(?:19|20)\d{2})\b)$", text, flags=re.I)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    return text, ""


def _draw_entry_heading(c, y, heading):
    heading = _safe(heading)
    if not heading:
        return y

    left_text, right_text = _split_heading_date(heading)
    y = _ensure_space(c, y, 20)

    _set(c, "Helvetica-Bold", HEADING_SIZE, TEXT_COLOR)
    if right_text:
        right_w = c.stringWidth(right_text, "Helvetica", BODY_SIZE)
        max_left_width = (RIGHT - LEFT) - right_w - 16
        left_lines = _wrap(left_text, font="Helvetica-Bold", size=HEADING_SIZE, width=max_left_width, c=c)

        c.drawString(LEFT, y, left_lines[0] if left_lines else left_text)
        _set(c, "Helvetica", BODY_SIZE, TEXT_COLOR)
        c.drawString(RIGHT - right_w, y, right_text)

        for extra in left_lines[1:]:
            y -= 13
            _set(c, "Helvetica-Bold", HEADING_SIZE, TEXT_COLOR)
            c.drawString(LEFT, y, extra)
    else:
        left_lines = _wrap(left_text, font="Helvetica-Bold", size=HEADING_SIZE, width=RIGHT - LEFT, c=c)
        for i, line in enumerate(left_lines):
            if i > 0:
                y -= 13
            _set(c, "Helvetica-Bold", HEADING_SIZE, TEXT_COLOR)
            c.drawString(LEFT, y, line)

    return y - ENTRY_HEADING_GAP


def _normalize_languages(text):
    lines = []
    for raw in _safe(text).splitlines():
        s = _safe(raw).lstrip("-•* ").strip()
        if not s:
            continue
        s = s.replace(" - ", ", ")
        s = s.replace(" (", ", ").replace(")", "")
        lines.append(s)
    return lines


def _draw_labeled_skill_line(c, y, line):
    line = _safe(line)
    if not line:
        return y

    if ":" not in line:
        return _draw_paragraph(c, y, line, size=BODY_SIZE, line_gap=PARA_LINE_GAP) - 2

    label, rest = line.split(":", 1)
    label = label.strip() + ":"
    rest = rest.strip()

    y = _ensure_space(c, y, 18)
    _set(c, "Helvetica-Bold", BODY_SIZE, TEXT_COLOR)
    c.drawString(LEFT, y, label)
    x = LEFT + c.stringWidth(label + " ", "Helvetica-Bold", BODY_SIZE)

    lines = _wrap(rest, font="Helvetica", size=BODY_SIZE, width=RIGHT - x, c=c)
    if lines:
        _set(c, "Helvetica", BODY_SIZE, TEXT_COLOR)
        c.drawString(x, y, lines[0])
        for extra in lines[1:]:
            y -= PARA_LINE_GAP
            c.drawString(LEFT, y, extra)
    return y - 9


def _draw_text_section(c, y, title, body):
    body = _safe(body)
    if not body:
        return y

    if title.lower() == "technical skills":
        for line in body.splitlines():
            if _safe(line):
                y = _draw_labeled_skill_line(c, y, line)
        return y - 4

    if title.lower() == "languages":
        for line in _normalize_languages(body):
            y = _draw_paragraph(c, y, line, size=BODY_SIZE, line_gap=PARA_LINE_GAP) - 2
        return y - 4

    parts = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    if not parts:
        parts = [body]

    for part in parts:
        lines = [x.rstrip() for x in part.splitlines() if x.strip()]
        if not lines:
            continue

        heading = None
        bullets = []
        paras = []

        for i, line in enumerate(lines):
            stripped = line.lstrip()
            if stripped.startswith(("-", "•", "*")):
                bullets.append(stripped.lstrip("-•* ").strip())
            else:
                if i == 0 and (len(lines) > 1 or title.lower() in {"experience", "selected projects", "education", "projects"}):
                    heading = line.strip()
                else:
                    paras.append(line.strip())

        if heading:
            y = _draw_entry_heading(c, y, heading)

        for para in paras:
            y = _draw_paragraph(c, y, para, size=BODY_SIZE, line_gap=PARA_LINE_GAP) - 3

        for bullet in bullets:
            y = _draw_bullet(c, y, bullet, bullet="•", size=BODY_SIZE)

        y -= 4

    return y


def _contact_items(contacts):
    contacts = contacts or {}
    email = _safe(contacts.get("email"))
    phone = _safe(contacts.get("phone"))
    location = _safe(contacts.get("location"))
    linkedin = _normalize_url(contacts.get("linkedin_url") or contacts.get("linkedin"))
    github = _normalize_url(contacts.get("github_url") or contacts.get("github"))
    website = _normalize_url(contacts.get("website_url") or contacts.get("website"))

    items = []
    if email:
        items.append(("textlink", email, "mailto:" + email))
    if phone:
        items.append(("text", phone, ""))
    if location:
        items.append(("text", location, ""))
    if linkedin:
        items.append(("label", "LinkedIn", linkedin))
    if github:
        items.append(("label", "GitHub", github))
    if website:
        items.append(("label", "Website", website))
    return items


def _draw_contact_row(c, y, contacts):
    items = _contact_items(contacts)
    if not items:
        return y

    parts = []
    total_w = 0
    sep = " | "
    sep_w = c.stringWidth(sep, "Helvetica", CONTACT_SIZE)

    for kind, label, url in items:
        w = c.stringWidth(label, "Helvetica", CONTACT_SIZE)
        parts.append((kind, label, url, w))
        total_w += w

    total_w += sep_w * max(0, len(parts) - 1)
    x = max(LEFT, (PAGE_W - total_w) / 2.0)

    for idx, (kind, label, url, w) in enumerate(parts):
        if kind == "text":
            _set(c, "Helvetica", CONTACT_SIZE, TEXT_COLOR)
            c.drawString(x, y, label)
        else:
            _draw_link(c, x, y, label, url, font="Helvetica", size=CONTACT_SIZE)
        x += w
        if idx < len(parts) - 1:
            _set(c, "Helvetica", CONTACT_SIZE, MUTED_COLOR)
            c.drawString(x, y, sep)
            x += sep_w
    return y


def export_cv_pdf(path, name, headline="", contacts=None, summary="", sections=None):
    c = canvas.Canvas(path, pagesize=A4)
    y = TOP

    name = _safe(name)
    headline = _safe(headline)
    summary = _safe(summary)
    sections = sections or []

    y = _draw_centered(c, y, name, font="Helvetica-Bold", size=NAME_SIZE, color=NAME_COLOR)
    y -= HEADER_GAP_AFTER_NAME

    if headline:
        y = _draw_centered(c, y, headline, font="Helvetica", size=HEADLINE_SIZE, color=MUTED_COLOR)
        y -= HEADER_GAP_AFTER_HEADLINE

    y = _draw_contact_row(c, y, contacts or {})
    y -= HEADER_GAP_AFTER_CONTACTS
    _hr(c, y)
    y -= 20

    if summary:
        y = _draw_section_title(c, y, "Professional Summary")
        y = _draw_paragraph(c, y, summary, size=BODY_SIZE, line_gap=PARA_LINE_GAP)
        y -= SECTION_BOTTOM_GAP

    normalized_sections = []
    for sec in sections:
        if isinstance(sec, dict):
            normalized_sections.append((_safe(sec.get("title")), _safe(sec.get("body")), _safe(sec.get("kind") or "text")))
        elif isinstance(sec, (list, tuple)) and len(sec) >= 2:
            title = _safe(sec[0])
            body = _safe(sec[1])
            kind = _safe(sec[2]) if len(sec) >= 3 else "text"
            normalized_sections.append((title, body, kind))

    for title, body, kind in normalized_sections:
        if not _safe(title) or not _safe(body):
            continue
        y = _draw_section_title(c, y, title)
        y = _draw_text_section(c, y, title, body)
        y -= SECTION_BOTTOM_GAP

    c.save()


# ---------- Hebrew / RTL helpers ----------

def _ensure_hebrew_font():
    if HEBREW_FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return HEBREW_FONT_NAME

    candidates = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\Arial.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
        r"C:\Windows\Fonts\Tahoma.ttf",
        r"C:\Windows\Fonts\david.ttf",
        r"C:\Windows\Fonts\David.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(HEBREW_FONT_NAME, path))
            return HEBREW_FONT_NAME

    # fallback to Helvetica if no Hebrew-capable font found
    return "Helvetica"


def _rtl(text: str) -> str:
    text = _safe(text)
    if not text:
        return ""
    if bidi_get_display:
        try:
            return bidi_get_display(text)
        except Exception:
            return text
    return text


def _draw_right(c, y, text, font, size, color=TEXT_COLOR):
    text = _rtl(text)
    _set(c, font, size, color)
    w = c.stringWidth(text, font, size)
    c.drawString(RIGHT - w, y, text)


def _wrap_rtl(c, text, font, size, width):
    text = _safe(text)
    if not text:
        return []

    words = text.split()
    if not words:
        return []

    lines = []
    current = words[0]

    for word in words[1:]:
        test = current + " " + word
        test_disp = _rtl(test)
        w = c.stringWidth(test_disp, font, size)
        if w <= width:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _draw_centered_rtl(c, y, text, font, size, color=TEXT_COLOR):
    text = _rtl(text)
    _set(c, font, size, color)
    w = c.stringWidth(text, font, size)
    c.drawString((PAGE_W - w) / 2.0, y, text)
    return y


def _draw_paragraph_rtl(c, y, text, font, size, color=TEXT_COLOR, line_gap=PARA_LINE_GAP):
    lines = _wrap_rtl(c, text, font, size, RIGHT - LEFT)
    if not lines:
        return y
    y = _ensure_space(c, y, len(lines) * line_gap + 6)
    for line in lines:
        _draw_right(c, y, line, font, size, color)
        y -= line_gap
    return y


def _draw_bullet_rtl(c, y, text, font, size=BODY_SIZE):
    text = _safe(text)
    if not text:
        return y

    lines = _wrap_rtl(c, text, font, size, RIGHT - LEFT - 18)
    if not lines:
        return y

    y = _ensure_space(c, y, len(lines) * BULLET_LINE_GAP + 4)

    _set(c, font, size, TEXT_COLOR)
    bullet_w = c.stringWidth("•", font, size)
    c.drawString(RIGHT - bullet_w, y, "•")

    first = _rtl(lines[0])
    w = c.stringWidth(first, font, size)
    c.drawString(RIGHT - 14 - w, y, first)

    for line in lines[1:]:
        y -= BULLET_LINE_GAP
        disp = _rtl(line)
        w = c.stringWidth(disp, font, size)
        c.drawString(RIGHT - 14 - w, y, disp)

    return y - BULLET_LINE_GAP


def _draw_section_title_rtl(c, y, title, font):
    y -= SECTION_TOP_GAP
    y = _ensure_space(c, y, 34)
    _draw_right(c, y, title, font, SECTION_SIZE, SECTION_COLOR)
    y -= SECTION_RULE_GAP
    _hr(c, y)
    return y - SECTION_BODY_GAP


def _draw_text_section_rtl(c, y, title, body, font):
    body = _safe(body)
    if not body:
        return y

    if title == "שפות":
        for raw in body.splitlines():
            line = _safe(raw).lstrip("-•* ").strip()
            if line:
                line = line.replace(" - ", ", ").replace(" (", ", ").replace(")", "")
                y = _draw_paragraph_rtl(c, y, line, font, BODY_SIZE) - 2
        return y - 4

    if title == "כישורים טכניים":
        for raw in body.splitlines():
            line = _safe(raw)
            if not line:
                continue
            if ":" in line:
                a, b = line.split(":", 1)
                line = f"{a.strip()}: {b.strip()}"
            y = _draw_paragraph_rtl(c, y, line, font, BODY_SIZE) - 2
        return y - 4

    parts = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    if not parts:
        parts = [body]

    for part in parts:
        lines = [x.rstrip() for x in part.splitlines() if x.strip()]
        if not lines:
            continue

        heading = None
        bullets = []
        paras = []

        for i, line in enumerate(lines):
            stripped = line.lstrip()
            if stripped.startswith(("-", "•", "*")):
                bullets.append(stripped.lstrip("-•* ").strip())
            else:
                if i == 0 and len(lines) > 1:
                    heading = line.strip()
                else:
                    paras.append(line.strip())

        if heading:
            y = _ensure_space(c, y, 20)
            _draw_right(c, y, heading, font, HEADING_SIZE, TEXT_COLOR)
            y -= ENTRY_HEADING_GAP

        for para in paras:
            y = _draw_paragraph_rtl(c, y, para, font, BODY_SIZE) - 3

        for bullet in bullets:
            y = _draw_bullet_rtl(c, y, bullet, font, BODY_SIZE)

        y -= 4

    return y


def export_cv_pdf_he(path, name, headline="", contacts=None, summary="", sections=None):
    font = _ensure_hebrew_font()
    c = canvas.Canvas(path, pagesize=A4)
    y = TOP

    name = _safe(name)
    headline = _safe(headline)
    summary = _safe(summary)
    sections = sections or []

    y = _draw_centered_rtl(c, y, name, font, NAME_SIZE, NAME_COLOR)
    y -= HEADER_GAP_AFTER_NAME

    if headline:
        y = _draw_centered_rtl(c, y, headline, font, HEADLINE_SIZE, MUTED_COLOR)
        y -= HEADER_GAP_AFTER_HEADLINE

    # contact row stays centered; mixed English/Hebrew is acceptable here
    y = _draw_contact_row(c, y, contacts or {})
    y -= HEADER_GAP_AFTER_CONTACTS
    _hr(c, y)
    y -= 20

    if summary:
        y = _draw_section_title_rtl(c, y, "תקציר מקצועי", font)
        y = _draw_paragraph_rtl(c, y, summary, font, BODY_SIZE)
        y -= SECTION_BOTTOM_GAP

    title_map = {
        "Technical Skills": "כישורים טכניים",
        "Languages": "שפות",
        "Selected Projects": "פרויקטים נבחרים",
        "Experience": "ניסיון",
        "Education": "השכלה",
    }

    normalized_sections = []
    for sec in sections:
        if isinstance(sec, dict):
            normalized_sections.append((_safe(sec.get("title")), _safe(sec.get("body")), _safe(sec.get("kind") or "text")))
        elif isinstance(sec, (list, tuple)) and len(sec) >= 2:
            title = _safe(sec[0])
            body = _safe(sec[1])
            kind = _safe(sec[2]) if len(sec) >= 3 else "text"
            normalized_sections.append((title, body, kind))

    for title, body, kind in normalized_sections:
        if not _safe(title) or not _safe(body):
            continue
        he_title = title_map.get(title, title)
        y = _draw_section_title_rtl(c, y, he_title, font)
        y = _draw_text_section_rtl(c, y, he_title, body, font)
        y -= SECTION_BOTTOM_GAP

    c.save()


def export_cover_letter_pdf(path, name, contacts, letter_text, headline="", date_str=""):
    c = canvas.Canvas(path, pagesize=A4)
    y = TOP

    name = _safe(name)
    headline = _safe(headline)
    letter_text = _safe(letter_text)
    date_str = _safe(date_str)

    y = _draw_centered(c, y, name, font="Helvetica-Bold", size=24, color=NAME_COLOR)
    y -= 18

    if headline:
        y = _draw_centered(c, y, headline, font="Helvetica", size=11.5, color=MUTED_COLOR)
        y -= 14

    y = _draw_contact_row(c, y, contacts or {})
    y -= 14
    _hr(c, y)
    y -= 22

    if date_str:
        _set(c, "Helvetica", BODY_SIZE, TEXT_COLOR)
        c.drawString(LEFT, y, date_str)
        y -= 20

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", letter_text) if p.strip()]
    for para in paragraphs:
        y = _draw_paragraph(c, y, para, size=BODY_SIZE, line_gap=PARA_LINE_GAP)
        y -= 8

    c.save()
