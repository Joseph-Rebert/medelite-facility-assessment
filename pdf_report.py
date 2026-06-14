import os
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from report_data import build_rows

_FONT_DIR = os.path.join(os.path.dirname(__file__), "assets", "fonts")
pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(_FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(_FONT_DIR, "DejaVuSans-Bold.ttf")))

BRAND = colors.HexColor("#0B7285")
INK = colors.HexColor("#212529")
LIGHT = colors.HexColor("#E9F5F7")

_styles = getSampleStyleSheet()
_brand_style = ParagraphStyle(
    "Brand", parent=_styles["Normal"], fontName="Helvetica-Bold",
    fontSize=16, textColor=colors.white, alignment=TA_CENTER,
)
_title_style = ParagraphStyle(
    "Title", parent=_styles["Normal"], fontName="Helvetica-Bold",
    fontSize=20, leading=26, textColor=INK, alignment=TA_CENTER,
    spaceBefore=12, spaceAfter=4,
)
_state_style = ParagraphStyle(
    "State", parent=_styles["Normal"], fontName="Helvetica-Bold",
    fontSize=13, leading=16, textColor=BRAND, alignment=TA_CENTER, spaceAfter=6,
)
_link_style = ParagraphStyle(
    "Link", parent=_styles["Normal"], fontSize=9, alignment=TA_CENTER, spaceBefore=18,
)
_cell_style = ParagraphStyle("Cell", parent=_styles["Normal"], fontSize=10, leading=13)
_label_style = ParagraphStyle("Label", parent=_cell_style, fontName="Helvetica-Bold")
_star_style = ParagraphStyle("Star", parent=_cell_style, fontName="DejaVu", fontSize=11)


def _stars(value):
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return Paragraph(str(value) if value else "N/A", _cell_style)
    filled = f'<font color="#E8A317">{"★" * n}</font>'
    empty = f'<font color="#C4C7C5">{"★" * (5 - n)}</font>'
    return Paragraph(f"{filled}{empty}  ({n}/5)", _star_style)


_section_style = ParagraphStyle(
    "Section", parent=_cell_style, fontName="Helvetica-Bold",
    fontSize=11, textColor=colors.white,
)

def build_pdf(data):
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )

    brand_bar = Table(
        [[Paragraph("INFINITE — Managed by MEDELITE", _brand_style)]],
        colWidths=[doc.width],
    )
    brand_bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))

    table_data = []
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C4C7C5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]
    for i, (kind, label, value) in enumerate(build_rows(data)):
        if kind == "section":
            table_data.append([Paragraph(label, _section_style), ""])
            style += [
                ("SPAN", (0, i), (1, i)),
                ("BACKGROUND", (0, i), (-1, i), BRAND),
            ]
        else:
            cell = _stars(value) if kind == "rating" else Paragraph(str(value), _cell_style)
            table_data.append([Paragraph(label, _label_style), cell])
            style.append(("BACKGROUND", (0, i), (0, i), LIGHT))

    body = Table(table_data, colWidths=[doc.width * 0.45, doc.width * 0.55])
    body.setStyle(TableStyle(style))

    link = data.get("source_url", "")
    elements = [
        brand_bar,
        Paragraph("FACILITY ASSESSMENT SNAPSHOT", _title_style),
        Paragraph(data.get("state", ""), _state_style),
        Spacer(1, 10),
        body,
        Paragraph(f'Source: <a href="{link}" color="blue">{link}</a>', _link_style),
    ]
    doc.build(elements)
    buf.seek(0)
    return buf.getvalue()
