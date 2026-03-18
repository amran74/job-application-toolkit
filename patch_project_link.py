from pathlib import Path
import re

p = Path("jobtracker/lib/pdf_export.py")
txt = p.read_text(encoding="utf-8")

# locate bullet renderer
pattern = r'def _draw_bullet\(.*?\):.*?return y - 14'
m = re.search(pattern, txt, flags=re.S)

if not m:
    raise SystemExit("Could not find bullet renderer")

new_func = '''
def _draw_bullet(c, y, text, bullet="•", size=10.4):
    import re
    url_match = re.search(r'https?://\\S+', text)

    if url_match:
        url = url_match.group(0)
        text = "Project link"

        y = _ensure_space(c, y, 16)
        _set(c, "Helvetica", size, TEXT_COLOR)
        c.drawString(LEFT, y, bullet)

        x = LEFT + 14
        w = _draw_link(c, x, y, text, url, "Helvetica", size)
        return y - 14

    lines = _wrap(text, font="Helvetica", size=size, width=(RIGHT - LEFT - 18), c=c)

    if not lines:
        return y

    y = _ensure_space(c, y, len(lines) * 13 + 4)

    _set(c, "Helvetica", size, TEXT_COLOR)
    c.drawString(LEFT, y, bullet)
    c.drawString(LEFT + 14, y, lines[0])

    for line in lines[1:]:
        y -= 13
        c.drawString(LEFT + 14, y, line)

    return y - 14
'''

txt = txt[:m.start()] + new_func + txt[m.end():]

p.write_text(txt, encoding="utf-8")

print("Bullet renderer upgraded: URLs now appear as 'Project link'.")
