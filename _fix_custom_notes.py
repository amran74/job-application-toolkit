from pathlib import Path
import re

p = Path(r"jobtracker\pages\7_AI_CV_Generator.py")
txt = p.read_text(encoding="utf-8-sig")

# 1) Add custom notes textarea under Job Description
txt, n1 = re.subn(
    r'''with right:\r?\n(\s*)jd_text\s*=\s*st\.text_area\("Job description",\s*height=\d+,\s*value=job\.get\("jd_text"\)\s*or\s*""\)''',
    r'''with right:
\1jd_text = st.text_area("Job description", height=220, value=job.get("jd_text") or "")
\1custom_notes = st.text_area(
\1    "Custom notes for AI",
\1    height=110,
\1    placeholder="Example: Focus on BI and dashboards, mention leadership, keep it concise, emphasize customer-facing work..."
\1)''',
    txt,
    count=1,
    flags=re.S
)
if n1 == 0 and 'custom_notes = st.text_area(' not in txt:
    raise SystemExit("Could not patch Job Description area.")

# 2) Add custom_notes param to build_prompt definition
txt, n2 = re.subn(
    r'''def build_prompt\(\r?\n(.*?)\r?\n\):''',
    lambda m: (
        'def build_prompt(\n' +
        m.group(1) +
        ',\n    custom_notes: str\n):'
        if 'custom_notes: str' not in m.group(1) else m.group(0)
    ),
    txt,
    count=1,
    flags=re.S
)
if n2 == 0:
    raise SystemExit("Could not patch build_prompt definition.")

# 3) Inject custom notes into prompt body
if 'CUSTOM_NOTES_FROM_USER:' not in txt:
    txt, n3 = re.subn(
        r'''(Important:\r?\n.*?- Use polished hiring-friendly language\.\r?\n)(""")''',
        r'''\1
CUSTOM_NOTES_FROM_USER:
{custom_notes or "None"}
\2''',
        txt,
        count=1,
        flags=re.S
    )
    if n3 == 0:
        raise SystemExit("Could not patch prompt body with custom notes.")

# 4) Pass custom_notes into build_prompt call
txt, n4 = re.subn(
    r'''system_rules,\s*user_input\s*=\s*build_prompt\(\r?\n(.*?)\r?\n\s*\)''',
    lambda m: (
        'system_rules, user_input = build_prompt(\n' +
        m.group(1) +
        ('' if 'custom_notes=' in m.group(1) else ',\n        custom_notes=custom_notes.strip()') +
        '\n    )'
    ),
    txt,
    count=1,
    flags=re.S
)
if n4 == 0:
    raise SystemExit("Could not patch build_prompt call.")

p.write_text(txt, encoding="utf-8-sig")
print("Patched custom notes successfully.")
