from pathlib import Path
import re

p = Path("jobtracker/lib/ai_tools.py")
txt = p.read_text(encoding="utf-8")

# Replace broken Responses API usage with simple chat completion
txt = re.sub(
    r'client\.responses\.create\((.*?)\)',
'''client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a professional resume writer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4
    )''',
    txt,
    flags=re.S
)

txt = txt.replace("response.output_text", "response.choices[0].message.content")

p.write_text(txt, encoding="utf-8")

print("AI generator API fixed.")
