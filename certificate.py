from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


COURSE_TITLES = {
    "data-structures": "Data Structures",
    "computer-architecture": "Computer Architecture",
}


def _draw_background(pdf, width, height):
    """Draw a clean green-and-gold certificate background."""
    dark = HexColor("#075A39")
    deep = HexColor("#043E29")
    green = HexColor("#159B54")
    light_green = HexColor("#AEE6C7")
    pale_green = HexColor("#E8F7EF")
    gold = HexColor("#D9B64A")

    # White base.
    pdf.setFillColor(colors.white)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)

    # Top-left green sweep.
    path = pdf.beginPath()
    path.moveTo(0, height)
    path.lineTo(105, height)
    path.curveTo(78, height - 65, 53, height - 135, 38, height - 220)
    path.curveTo(24, height - 305, 11, height - 370, 0, height - 415)
    path.close()
    pdf.setFillColor(deep)
    pdf.drawPath(path, stroke=0, fill=1)

    path = pdf.beginPath()
    path.moveTo(0, height)
    path.lineTo(153, height)
    path.curveTo(115, height - 63, 88, height - 136, 72, height - 222)
    path.curveTo(57, height - 305, 36, height - 375, 0, height - 438)
    path.close()
    pdf.setFillColor(green)
    pdf.drawPath(path, stroke=0, fill=1)

    path = pdf.beginPath()
    path.moveTo(0, height)
    path.lineTo(188, height)
    path.curveTo(146, height - 52, 113, height - 116, 94, height - 186)
    path.curveTo(75, height - 255, 50, height - 320, 19, height - 379)
    path.close()
    pdf.setFillColor(pale_green)
    pdf.drawPath(path, stroke=0, fill=1)

    # Top-right green sweep.
    path = pdf.beginPath()
    path.moveTo(width, height)
    path.lineTo(width - 105, height)
    path.curveTo(width - 78, height - 65, width - 53, height - 135, width - 38, height - 220)
    path.curveTo(width - 24, height - 305, width - 11, height - 370, width, height - 415)
    path.close()
    pdf.setFillColor(deep)
    pdf.drawPath(path, stroke=0, fill=1)

    path = pdf.beginPath()
    path.moveTo(width, height)
    path.lineTo(width - 153, height)
    path.curveTo(width - 115, height - 63, width - 88, height - 136, width - 72, height - 222)
    path.curveTo(width - 57, height - 305, width - 36, height - 375, width, height - 438)
    path.close()
    pdf.setFillColor(green)
    pdf.drawPath(path, stroke=0, fill=1)

    path = pdf.beginPath()
    path.moveTo(width, height)
    path.lineTo(width - 188, height)
    path.curveTo(width - 146, height - 52, width - 113, height - 116, width - 94, height - 186)
    path.curveTo(width - 75, height - 255, width - 50, height - 320, width - 19, height - 379)
    path.close()
    pdf.setFillColor(pale_green)
    pdf.drawPath(path, stroke=0, fill=1)

    # Bottom corner sweeps.
    path = pdf.beginPath()
    path.moveTo(0, 0)
    path.lineTo(0, 88)
    path.curveTo(74, 73, 145, 40, 230, 0)
    path.close()
    pdf.setFillColor(deep)
    pdf.drawPath(path, stroke=0, fill=1)

    path = pdf.beginPath()
    path.moveTo(0, 0)
    path.lineTo(0, 60)
    path.curveTo(78, 48, 148, 25, 216, 0)
    path.close()
    pdf.setFillColor(green)
    pdf.drawPath(path, stroke=0, fill=1)

    path = pdf.beginPath()
    path.moveTo(width, 0)
    path.lineTo(width, 88)
    path.curveTo(width - 74, 73, width - 145, 40, width - 230, 0)
    path.close()
    pdf.setFillColor(deep)
    pdf.drawPath(path, stroke=0, fill=1)

    path = pdf.beginPath()
    path.moveTo(width, 0)
    path.lineTo(width, 60)
    path.curveTo(width - 78, 48, width - 148, 25, width - 216, 0)
    path.close()
    pdf.setFillColor(green)
    pdf.drawPath(path, stroke=0, fill=1)

    # Subtle curved line texture.
    pdf.setStrokeColor(light_green)
    pdf.setLineWidth(0.55)

    for i in range(5):
        inset = i * 9
        pdf.bezier(
            70 + inset,
            height - 10 - inset,
            260,
            height + 7 - inset,
            420,
            height - 6 - inset,
            575,
            height - 42 - inset,
        )
        pdf.bezier(
            width - 70 - inset,
            10 + inset,
            width - 260,
            -7 + inset,
            width - 420,
            6 + inset,
            width - 575,
            42 + inset,
        )

    # Gold corner accents.
    pdf.setStrokeColor(gold)
    pdf.setLineWidth(1.8)
    pdf.line(18, height - 70, 88, height - 18)
    pdf.line(width - 88, height - 18, width - 18, height - 70)
    pdf.line(18, 70, 88, 18)
    pdf.line(width - 88, 18, width - 18, 70)


def _draw_frame(pdf, width, height):
    gold = HexColor("#D9B64A")
    green = HexColor("#70C997")

    pdf.setStrokeColor(gold)
    pdf.setLineWidth(1.6)
    pdf.rect(18, 18, width - 36, height - 36, stroke=1, fill=0)

    pdf.setStrokeColor(green)
    pdf.setLineWidth(0.65)
    pdf.rect(28, 28, width - 56, height - 56, stroke=1, fill=0)


def _draw_logo(pdf, x, y, scale=1.0):
    green = HexColor("#159B54")
    dark = HexColor("#075A39")

    pdf.saveState()
    pdf.translate(x, y)

    path = pdf.beginPath()
    path.moveTo(-28 * scale, 30 * scale)
    path.lineTo(-28 * scale, -18 * scale)
    path.curveTo(-28 * scale, -27 * scale, -22 * scale, -31 * scale, -14 * scale, -25 * scale)
    path.lineTo(28 * scale, 10 * scale)
    path.curveTo(38 * scale, 17 * scale, 38 * scale, 28 * scale, 27 * scale, 33 * scale)
    path.lineTo(-12 * scale, 5 * scale)
    path.lineTo(-12 * scale, 33 * scale)
    path.close()
    pdf.setFillColor(green)
    pdf.drawPath(path, stroke=0, fill=1)

    path = pdf.beginPath()
    path.moveTo(2 * scale, 5 * scale)
    path.lineTo(28 * scale, -14 * scale)
    path.curveTo(35 * scale, -20 * scale, 35 * scale, -28 * scale, 28 * scale, -33 * scale)
    path.curveTo(21 * scale, -38 * scale, 15 * scale, -35 * scale, 8 * scale, -29 * scale)
    path.lineTo(-6 * scale, -18 * scale)
    path.close()
    pdf.setFillColor(dark)
    pdf.drawPath(path, stroke=0, fill=1)

    pdf.restoreState()


def _draw_badge(pdf, cx, cy):
    gold = HexColor("#D9B64A")
    dark = HexColor("#06432C")

    pdf.setFillColor(gold)
    pdf.circle(cx, cy, 41, stroke=0, fill=1)

    pdf.setFillColor(dark)
    pdf.circle(cx, cy, 34, stroke=0, fill=1)

    pdf.setStrokeColor(gold)
    pdf.setLineWidth(1.1)
    pdf.circle(cx, cy, 27, stroke=1, fill=0)

    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 6.5)
    pdf.drawCentredString(cx, cy + 10, "KNOWLEDGE")
    pdf.drawCentredString(cx, cy + 1, "BUILDS A")
    pdf.drawCentredString(cx, cy - 8, "BRIGHTER")
    pdf.drawCentredString(cx, cy - 17, "TOMORROW")


def _draw_laurel(pdf, x, y, side):
    leaf = HexColor("#DDEFE5")

    pdf.setStrokeColor(leaf)
    pdf.setLineWidth(1.25)
    pdf.bezier(
        x,
        y - 58,
        x + side * 18,
        y + 5,
        x + side * 28,
        y + 60,
        x + side * 38,
        y + 105,
    )

    for i in range(7):
        yy = y - 43 + i * 22
        xx = x + side * (8 + i * 3)

        pdf.setFillColor(leaf)
        pdf.ellipse(xx - 12, yy, xx + 4, yy + 9, stroke=0, fill=1)
        pdf.ellipse(xx - 3, yy + 5, xx + 13, yy + 15, stroke=0, fill=1)


def generate_certificate_pdf(user, course, progress):
    """
    Return a real, browser-readable PDF as an in-memory BytesIO object.

    Dynamic values:
      user["full_name"]
      course
      progress["completed_lessons"]
      progress["total"]

    Deliberately omitted:
      signature
      date
      certificate ID
      quiz marks
    """
    course = str(course or "").strip().lower()
    title = COURSE_TITLES.get(course)

    if not title:
        raise ValueError("Unsupported certificate course.")

    if not progress.get("completed"):
        raise ValueError("Course is not complete.")

    width, height = landscape(A4)
    buffer = BytesIO()

    # ReportLab writes a standards-compliant PDF directly.
    # This is intentionally not an image-to-PDF conversion, which is
    # what caused the browser preview problem in the previous version.
    pdf = canvas.Canvas(buffer, pagesize=(width, height))
    pdf.setTitle(f"NEXORA Certificate - {title}")
    pdf.setAuthor("NEXORA Learning Platform")
    pdf.setSubject(f"Certificate of Completion - {title}")

    _draw_background(pdf, width, height)
    _draw_frame(pdf, width, height)

    center_x = width / 2

    # Top-left NEXORA branding.
    _draw_logo(pdf, 105, height - 84, 0.82)

    pdf.setFillColor(HexColor("#075A39"))
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawString(72, height - 122, "NEXORA")

    pdf.setFillColor(HexColor("#65736C"))
    pdf.setFont("Helvetica", 6.8)
    pdf.drawString(72, height - 135, "LEARN  •  PRACTICE  •  GROW")

    # Top-right badge.
    _draw_badge(pdf, width - 106, height - 91)

    # Main title.
    pdf.setFillColor(HexColor("#064B31"))
    pdf.setFont("Times-Bold", 34)
    pdf.drawCentredString(center_x, height - 81, "CERTIFICATE")

    pdf.setFillColor(HexColor("#1F2823"))
    pdf.setFont("Times-Bold", 19)
    pdf.drawCentredString(center_x, height - 114, "OF COMPLETION")

    pdf.setStrokeColor(HexColor("#169B56"))
    pdf.setLineWidth(0.9)
    pdf.line(center_x - 151, height - 110, center_x - 112, height - 110)
    pdf.line(center_x + 112, height - 110, center_x + 151, height - 110)

    # Laurels.
    _draw_laurel(pdf, center_x - 176, height - 440, -1)
    _draw_laurel(pdf, center_x + 176, height - 440, 1)

    # Recipient.
    pdf.setFillColor(HexColor("#65736C"))
    pdf.setFont("Helvetica", 9.7)
    pdf.drawCentredString(center_x, height - 160, "THIS CERTIFIES THAT")

    pdf.setFillColor(HexColor("#075A39"))
    pdf.setFont("Times-BoldItalic", 30)
    pdf.drawCentredString(
        center_x,
        height - 210,
        user["full_name"].upper(),
    )

    pdf.setStrokeColor(HexColor("#49B980"))
    pdf.setLineWidth(0.9)
    pdf.line(center_x - 112, height - 221, center_x - 18, height - 221)
    pdf.line(center_x + 18, height - 221, center_x + 112, height - 221)

    pdf.setFillColor(HexColor("#159B54"))
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawCentredString(center_x, height - 219, "◆")

    # Course statement.
    pdf.setFillColor(HexColor("#2C342F"))
    pdf.setFont("Times-Roman", 12)
    pdf.drawCentredString(
        center_x,
        height - 262,
        "has successfully completed the course",
    )

    pdf.setFillColor(HexColor("#075A39"))
    pdf.setFont("Times-Bold", 24)
    pdf.drawCentredString(center_x, height - 298, title)

    # Professional wording.
    pdf.setFillColor(HexColor("#3F4943"))
    pdf.setFont("Times-Roman", 9.5)
    pdf.drawCentredString(
        center_x,
        height - 330,
        "This certificate is awarded in recognition of your dedication,",
    )
    pdf.drawCentredString(
        center_x,
        height - 345,
        "consistent effort and successful completion of all the topics",
    )
    pdf.drawCentredString(
        center_x,
        height - 360,
        "in this course.",
    )

    # Completed topics.
    completed = len(progress.get("completed_lessons", []))
    total = int(progress.get("total", 0))

    pill_w = 190
    pill_h = 29
    pill_x = center_x - pill_w / 2
    pill_y = height - 405

    pdf.setFillColor(HexColor("#E5F8ED"))
    pdf.setStrokeColor(HexColor("#A2DFC0"))
    pdf.setLineWidth(0.8)
    pdf.roundRect(
        pill_x,
        pill_y,
        pill_w,
        pill_h,
        14,
        stroke=1,
        fill=1,
    )

    # Cap icon.
    pdf.setFillColor(HexColor("#075A39"))
    cap = pdf.beginPath()
    cap.moveTo(pill_x + 13, pill_y + 16)
    cap.lineTo(pill_x + 27, pill_y + 22)
    cap.lineTo(pill_x + 41, pill_y + 16)
    cap.lineTo(pill_x + 27, pill_y + 10)
    cap.close()
    pdf.drawPath(cap, stroke=0, fill=1)
    pdf.rect(pill_x + 25, pill_y + 6, 4, 7, stroke=0, fill=1)

    pdf.setFillColor(HexColor("#075A39"))
    pdf.setFont("Helvetica-Bold", 9.5)
    pdf.drawString(
        pill_x + 49,
        pill_y + 9,
        f"Completed topics: {completed} / {total}",
    )

    # Footer.
    pdf.setStrokeColor(HexColor("#169B56"))
    pdf.setLineWidth(0.8)
    pdf.line(center_x - 80, 70, center_x - 18, 70)
    pdf.line(center_x + 18, 70, center_x + 80, 70)

    pdf.setFillColor(HexColor("#169B56"))
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawCentredString(center_x, 66, "◆")

    pdf.setFillColor(HexColor("#075A39"))
    pdf.setFont("Helvetica-Bold", 8.3)
    pdf.drawCentredString(center_x, 49, "EMPOWERING MINDS")

    pdf.setFillColor(HexColor("#68766F"))
    pdf.setFont("Helvetica", 7.3)
    pdf.drawCentredString(
        center_x,
        37,
        "THROUGH INTERACTIVE LEARNING",
    )

    # No signature, date, certificate ID, or quiz marks.

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return buffer


def save_certificate_png(*args, **kwargs):
    """
    Kept as a compatibility helper for standalone callers.
    The Flask app should use generate_certificate_pdf().
    """
    raise NotImplementedError(
        "This version generates a PDF directly. "
        "Use generate_certificate_pdf() for the application."
    )


# Standalone test.
if __name__ == "__main__":
    class _User:
        full_name = "ASHWIN"

    output = generate_certificate_pdf(
        {"full_name": "ASHWIN"},
        "data-structures",
        {
            "completed": True,
            "completed_lessons": [{} for _ in range(14)],
            "total": 14,
        },
    )

    test_path = Path("certificate_test.pdf")
    test_path.write_bytes(output.read())
    print(f"Saved: {test_path.resolve()}")
