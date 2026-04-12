from __future__ import annotations

import os
import re
from html import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _try_register_font(font_name: str, candidates: list[str]) -> bool:
    for path in candidates:
        if path and os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, path))
                return True
            except Exception:
                pass
    return False


def _setup_fonts():
    normal_font = "Helvetica"
    bold_font = "Helvetica-Bold"
    hebrew_normal = "Helvetica"
    hebrew_bold = "Helvetica-Bold"

    win = os.environ.get("WINDIR", r"C:\Windows")
    font_dir = os.path.join(win, "Fonts")

    arial_ok = _try_register_font("AppArial", [
        os.path.join(font_dir, "arial.ttf"),
        os.path.join(font_dir, "Arial.ttf"),
    ])
    arial_bold_ok = _try_register_font("AppArialBold", [
        os.path.join(font_dir, "arialbd.ttf"),
        os.path.join(font_dir, "Arialbd.ttf"),
    ])

    if arial_ok:
        normal_font = "AppArial"
        hebrew_normal = "AppArial"
    if arial_bold_ok:
        bold_font = "AppArialBold"
        hebrew_bold = "AppArialBold"

    return {
        "normal": normal_font,
        "bold": bold_font,
        "he_normal": hebrew_normal,
        "he_bold": hebrew_bold,
    }


FONTS = _setup_fonts()


def _make_styles(hebrew: bool = False):
    base = getSampleStyleSheet()
    font_normal = FONTS["he_normal"] if hebrew else FONTS["normal"]
    font_bold = FONTS["he_bold"] if hebrew else FONTS["bold"]
    align = TA_RIGHT if hebrew else TA_LEFT

    return {
        "name": ParagraphStyle(
            "Name",
            parent=base["Normal"],
            fontName=font_bold,
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            textColor=colors.black,
            spaceAfter=4,
        ),
        "headline": ParagraphStyle(
            "Headline",
            parent=base["Normal"],
            fontName=font_normal,
            fontSize=10.5,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#444444"),
            spaceAfter=8,
        ),
        "contacts": ParagraphStyle(
            "Contacts",
            parent=base["Normal"],
            fontName=font_normal,
            fontSize=9.2,
            leading=11.5,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#333333"),
            spaceAfter=10,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Normal"],
            fontName=font_bold,
            fontSize=11.2,
            leading=13,
            alignment=align,
            textColor=colors.HexColor("#1f1f1f"),
            spaceBefore=7,
            spaceAfter=4,
        ),
        "summary": ParagraphStyle(
            "Summary",
            parent=base["Normal"],
            fontName=font_normal,
            fontSize=9.8,
            leading=13,
            alignment=align,
            textColor=colors.black,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName=font_normal,
            fontSize=9.6,
            leading=12.8,
            alignment=align,
            textColor=colors.black,
            spaceAfter=2,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontName=font_normal,
            fontSize=9.5,
            leading=12.5,
            alignment=align,
            leftIndent=10 if not hebrew else 0,
            rightIndent=0 if not hebrew else 10,
            firstLineIndent=0,
            bulletIndent=0,
            textColor=colors.black,
            spaceAfter=1.5,
        ),
        "cover_body": ParagraphStyle(
            "CoverBody",
            parent=base["Normal"],
            fontName=font_normal,
            fontSize=10.2,
            leading=14,
            alignment=TA_LEFT,
            textColor=colors.black,
            spaceAfter=4,
        ),
    }


def _safe(value) -> str:
    return escape(str(value or "").strip())


def _normalize_url(url: str) -> str:
    url = str(url or "").strip()
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return "https://" + url


def _link(label: str, url: str) -> str:
    url = _normalize_url(url)
    if not url:
        return _safe(label)
    return f'<link href="{_safe(url)}" color="blue"><u>{_safe(label)}</u></link>'


def _contact_line(contacts: dict) -> str:
    parts = []
    if contacts.get("email"):
        parts.append(_safe(contacts["email"]))
    if contacts.get("phone"):
        parts.append(_safe(contacts["phone"]))
    if contacts.get("location"):
        parts.append(_safe(contacts["location"]))
    if contacts.get("github_url"):
        parts.append(_link("GitHub", contacts["github_url"]))
    if contacts.get("linkedin_url"):
        parts.append(_link("LinkedIn", contacts["linkedin_url"]))
    if contacts.get("website_url"):
        parts.append(_link("Website", contacts["website_url"]))
    return " | ".join([p for p in parts if p])


_md_link_re = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _convert_md_links(text: str) -> str:
    def repl(match):
        label = match.group(1)
        url = match.group(2)
        return _link(label, url)
    return _md_link_re.sub(repl, _safe(text))


def _split_lines(text: str) -> list[str]:
    return [x.strip() for x in str(text or "").replace("\r\n", "\n").split("\n") if x.strip()]


def _add_multiline_text(story, text: str, style, bullet_style=None, links=False):
    bullet_char = chr(8226)

    for line in _split_lines(text):
        line_clean = line.lstrip()
        is_bullet = line_clean.startswith(bullet_char) or line_clean.startswith("-")
        payload = line_clean.lstrip(bullet_char + "- ").strip()
        html = _convert_md_links(payload if is_bullet else line) if links else _safe(payload if is_bullet else line)

        if is_bullet and bullet_style is not None:
            story.append(Paragraph(f"{bullet_char} {html}", bullet_style))
        else:
            story.append(Paragraph(html, style))


def _build_cv(path: str, name: str, headline: str, contacts: dict, summary: str, sections, hebrew: bool = False):
    styles = _make_styles(hebrew=hebrew)
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"{name} CV",
    )

    story = []
    story.append(Paragraph(_safe(name), styles["name"]))

    if str(headline or "").strip():
        story.append(Paragraph(_safe(headline), styles["headline"]))

    contact_line = _contact_line(contacts or {})
    if contact_line:
        story.append(Paragraph(contact_line, styles["contacts"]))

    if str(summary or "").strip():
        story.append(Paragraph(_safe("Summary" if not hebrew else "Summary"), styles["section"]))
        story.append(Paragraph(_safe(summary), styles["summary"]))
        story.append(Spacer(1, 2))

    for section in sections or []:
        if not section or len(section) < 2:
            continue

        title = section[0]
        content = section[1]
        mode = section[2] if len(section) > 2 else "text"

        if not str(content or "").strip():
            continue

        story.append(Paragraph(_safe(title), styles["section"]))

        if mode in ("bullets", "text", "bullets_links", "text_links"):
            _add_multiline_text(
                story,
                content,
                styles["body"],
                bullet_style=styles["bullet"],
                links=("links" in mode),
            )
        else:
            _add_multiline_text(story, content, styles["body"], bullet_style=styles["bullet"])

        story.append(Spacer(1, 2))

    doc.build(story)


def export_cv_pdf(path: str, name: str, headline: str, contacts: dict, summary: str, sections):
    _build_cv(path=path, name=name, headline=headline, contacts=contacts, summary=summary, sections=sections, hebrew=False)


def export_cv_pdf_he(path: str, name: str, headline: str, contacts: dict, summary: str, sections):
    _build_cv(path=path, name=name, headline=headline, contacts=contacts, summary=summary, sections=sections, hebrew=True)


def export_cover_letter_pdf(path: str, name: str, contacts: dict, letter_text: str, headline: str = "", date_str: str = ""):
    styles = _make_styles(hebrew=False)
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"{name} Cover Letter",
    )

    story = []
    story.append(Paragraph(_safe(name), styles["name"]))

    if str(headline or "").strip():
        story.append(Paragraph(_safe(headline), styles["headline"]))

    contact_line = _contact_line(contacts or {})
    if contact_line:
        story.append(Paragraph(contact_line, styles["contacts"]))

    if str(date_str or "").strip():
        story.append(Paragraph(_safe(date_str), styles["body"]))
        story.append(Spacer(1, 6))

    for para in str(letter_text or "").replace("\r\n", "\n").split("\n\n"):
        para = para.strip()
        if not para:
            continue
        story.append(Paragraph(_safe(para).replace("\n", "<br/>"), styles["cover_body"]))
        story.append(Spacer(1, 4))

    doc.build(story)
