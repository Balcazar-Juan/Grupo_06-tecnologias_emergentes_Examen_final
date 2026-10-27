from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_certificate(student: dict, enrollment: dict, courses: list[dict]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("<b>UNIVERSIDAD NACIONAL FEDERICO VILLARREAL</b>", styles["Title"]),
        Paragraph("FACULTAD DE INGENIERÍA INDUSTRIAL Y DE SISTEMAS", styles["Heading2"]),
        Paragraph("OFICINA TÉCNICA DE SERVICIOS ACADÉMICOS", styles["Normal"]),
        Spacer(1, 8 * mm),
        Paragraph("<b>CONSTANCIA DE MATRÍCULA 2026</b>", styles["Heading1"]),
        Spacer(1, 5 * mm),
    ]
    details = [["Escuela", student["program_name"], "Plan", student["plan"]], ["Alumno", student["full_name"], "Código", student["student_code"]], ["Periodo", enrollment["period"], "Estado", enrollment["status"]]]
    details_table = Table(details, colWidths=[24 * mm, 78 * mm, 22 * mm, 45 * mm])
    details_table.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 8), ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#596579")), ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#596579")), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.extend([details_table, Spacer(1, 5 * mm)])
    rows = [["N.°", "Periodo", "Código", "Sección", "Asignatura", "Créditos"]]
    total = 0
    for index, course in enumerate(courses, start=1):
        total += course["credits"]
        rows.append([index, enrollment["period"], course["code"], course.get("section", "A"), course["name"].upper(), course["credits"]])
    rows.append(["", "", "", "", "TOTAL DE CRÉDITOS", total])
    table = Table(rows, repeatRows=1, colWidths=[10 * mm, 23 * mm, 23 * mm, 17 * mm, 84 * mm, 18 * mm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#53617D")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#53617D")), ("TEXTCOLOR", (0, -1), (-1, -1), colors.white), ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#8B96A8")), ("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 7), ("ALIGN", (0, 0), (3, -1), "CENTER"), ("ALIGN", (-1, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.extend([table, Spacer(1, 18 * mm), Paragraph("______________________________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;______________________________", styles["Normal"]), Paragraph("Firma del alumno&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Oficina Técnica Académica", styles["Normal"]), Spacer(1, 10 * mm), Paragraph(f"Código de verificación: {enrollment['request_id']}-{student['student_code']}", styles["Normal"])])
    doc.build(story)
    return buffer.getvalue()
