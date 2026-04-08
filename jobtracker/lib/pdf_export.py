from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

def generate_cv(data, output_path="cv_output.pdf"):
    doc = SimpleDocTemplate(output_path, pagesize=A4)

    name_style = ParagraphStyle(
        'Name',
        fontSize=20,
        leading=24,
        spaceAfter=10,
        textColor=colors.black
    )

    section_style = ParagraphStyle(
        'Section',
        fontSize=12,
        leading=14,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#444444")
    )

    body_style = ParagraphStyle(
        'Body',
        fontSize=10,
        leading=14,
        spaceAfter=4
    )

    story = []

    story.append(Paragraph(data.get("name", "Your Name"), name_style))
    story.append(Spacer(1, 8))

    contact = data.get("contact", "")
    if contact:
        story.append(Paragraph(contact, body_style))
        story.append(Spacer(1, 10))

    summary = data.get("summary", "")
    if summary:
        story.append(Paragraph("Summary", section_style))
        story.append(Paragraph(summary, body_style))

    experience = data.get("experience", [])
    if experience:
        story.append(Paragraph("Experience", section_style))
        for exp in experience:
            title = f"<b>{exp.get('role','')}</b> - {exp.get('company','')}"
            story.append(Paragraph(title, body_style))
            story.append(Paragraph(exp.get("description",""), body_style))

    education = data.get("education", [])
    if education:
        story.append(Paragraph("Education", section_style))
        for edu in education:
            line = f"{edu.get('degree','')} - {edu.get('school','')}"
            story.append(Paragraph(line, body_style))

    doc.build(story)

if __name__ == "__main__":
    sample_data = {
        "name": "Amran",
        "contact": "Email | Phone | LinkedIn",
        "summary": "Information Systems graduate focused on data and analytics.",
        "experience": [
            {
                "role": "Shift Manager",
                "company": "Super-Pharm",
                "description": "Managed operations, staff coordination, and performance during shifts."
            }
        ],
        "education": [
            {
                "degree": "B.Sc. Information Systems",
                "school": "Your University"
            }
        ]
    }

    generate_cv(sample_data)
