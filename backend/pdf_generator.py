
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


OUTPUT_DIR = Path(__file__).resolve().parent.parent / "generated_pdfs"


def generate_document_pdf(document_data: dict) -> str:
    """Generate a draft PDF and return its file path."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf_path = OUTPUT_DIR / "income_certificate_draft.pdf"

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CivicBridgeTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#174A7E"),
    )

    story = [
        Paragraph("CivicBridge", title_style),
        Paragraph(
            "Income Certificate — Document Assistance Draft",
            styles["Heading2"],
        ),
        Spacer(1, 12),
        Paragraph(
            "DRAFT — NOT AN OFFICIAL GOVERNMENT FORM",
            styles["Heading3"],
        ),
        Spacer(1, 12),
        Paragraph(
            "This document summarizes information provided by the user. "
            "It is not an issued certificate or a submitted application.",
            styles["BodyText"],
        ),
        Spacer(1, 18),
    ]

    rows = [["Field", "Information"]]

    labels = {
        "applicant_name": "Applicant Name",
        "residential_address": "Residential Address",
        "annual_family_income": "Annual Family Income (INR)",
        "purpose": "Purpose",
    }

    answers = document_data.get("answers", {})

    for key, label in labels.items():
        value = str(answers.get(key, "Not provided"))
        rows.append([label, value])

    table = Table(rows, colWidths=[6 * cm, 10 * cm], repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#174A7E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))

    story.append(table)
    story.append(Spacer(1, 20))

    official_url = document_data.get("official_url", "")
    if official_url:
        story.append(Paragraph(
            f"Official portal: {official_url}",
            styles["BodyText"],
        ))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "Please verify the requirements and submit your application "
        "through the appropriate official government portal.",
        styles["Italic"],
    ))

    doc.build(story)

    return str(pdf_path)
