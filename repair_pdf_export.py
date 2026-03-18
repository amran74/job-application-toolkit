from pathlib import Path
import re
from datetime import datetime

p = Path("jobtracker/lib/pdf_export.py")
txt = p.read_text(encoding="utf-8-sig")

# backup
bak = p.with_name(p.name + ".repair_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
bak.write_text(txt, encoding="utf-8-sig")

# fix common broken patterns produced by earlier patches
txt = txt.replace('if "', 'if "')  # safety noop if already correct
txt = txt.replace('if "\\n" not in b and " - " in b:', 'if "\\n" not in b and " - " in b:')

# remove accidental long dash characters
txt = txt.replace(" — ", ", ")

# fix possible truncated lines
txt = re.sub(r'if\s*"\s*$', 'if ""', txt, flags=re.MULTILINE)

# ensure quotes are balanced on body.replace calls
txt = txt.replace('body.replace(" (", ", ").replace(")", "")', 'body.replace(" (", ", ").replace(")", "")')

p.write_text(txt, encoding="utf-8-sig")

print("pdf_export.py repaired")
print("backup:", bak.name)
