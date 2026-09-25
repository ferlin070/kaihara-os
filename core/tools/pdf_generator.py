"""
PDF Generator — Professional reports with Kaihara OS + Ghazwah Group branding.
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable
)
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate, Frame

logger = logging.getLogger("kaihara.pdf_generator")

OUTPUT_DIR = Path(os.getenv("KAIHARA_OUTPUT_DIR", "outputs/pdfs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PRIMARY = HexColor("#7c3aed")
PRIMARY_DARK = HexColor("#5b21b6")
ACCENT = HexColor("#a78bfa")
BG_LIGHT = HexColor("#f5f3ff")
TEXT_DARK = HexColor("#1e1b4b")
TEXT_MED = HexColor("#4c1d95")
TEXT_LIGHT = HexColor("#6b7280")
BORDER = HexColor("#e5e7eb")
WHITE = white


class KaiharaDocTemplate(BaseDocTemplate):
    def __init__(self, filename, **kwargs):
        self.report_title = kwargs.pop("report_title", "Report")
        self.author = kwargs.pop("author", "Kaihara OS")
        super().__init__(filename, **kwargs)
        frame = Frame(20*mm, 25*mm, self.width, self.height, id="main")
        template = PageTemplate(id="main", frames=[frame], onPage=self._draw_header_footer)
        self.addPageTemplates([template])

    def _draw_header_footer(self, canvas, doc):
        canvas.saveState()
        w, h = A4
        canvas.setFillColor(PRIMARY)
        canvas.rect(0, h - 22*mm, w, 22*mm, fill=1, stroke=0)
        canvas.setStrokeColor(ACCENT)
        canvas.setLineWidth(1)
        canvas.line(0, h - 22*mm, w, h - 22*mm)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString(20*mm, h - 14*mm, "KAIHARA OS")
        canvas.setFont("Helvetica", 9)
        canvas.drawString(20*mm, h - 19*mm, "AI Super-Intelligence Platform")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(w - 20*mm, h - 14*mm, datetime.now().strftime("%d %B %Y"))
        canvas.drawRightString(w - 20*mm, h - 19*mm, "nakhodacloud.top")
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(20*mm, 20*mm, w - 20*mm, 20*mm)
        canvas.setFillColor(TEXT_LIGHT)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(20*mm, 14*mm, "Ghazwah Group — Powered by Kaihara OS")
        canvas.drawRightString(w - 20*mm, 14*mm, f"Page {doc.page}")
        canvas.setFillColor(PRIMARY)
        canvas.circle(w/2, 14*mm, 2, fill=1, stroke=0)
        canvas.restoreState()


def _get_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", fontName="Helvetica-Bold", fontSize=22, leading=28, textColor=PRIMARY_DARK, spaceAfter=4*mm))
    styles.add(ParagraphStyle(name="ReportSubtitle", fontName="Helvetica", fontSize=11, leading=15, textColor=TEXT_LIGHT, spaceAfter=8*mm))
    styles.add(ParagraphStyle(name="SectionHeading", fontName="Helvetica-Bold", fontSize=14, leading=20, textColor=PRIMARY_DARK, spaceBefore=8*mm, spaceAfter=4*mm))
    styles.add(ParagraphStyle(name="SubHeading", fontName="Helvetica-Bold", fontSize=11, leading=15, textColor=TEXT_MED, spaceBefore=5*mm, spaceAfter=3*mm))
    styles.add(ParagraphStyle(name="BodyText2", fontName="Helvetica", fontSize=10, leading=15, textColor=TEXT_DARK, spaceAfter=3*mm, alignment=TA_JUSTIFY))
    styles.add(ParagraphStyle(name="BulletItem", fontName="Helvetica", fontSize=10, leading=14, textColor=TEXT_DARK, leftIndent=12*mm, bulletIndent=6*mm, spaceAfter=2*mm))
    styles.add(ParagraphStyle(name="SmallGray", fontName="Helvetica", fontSize=8, leading=11, textColor=TEXT_LIGHT))
    return styles


def _make_section_divider():
    return HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceAfter=4*mm, spaceBefore=2*mm)


def _make_highlight_box(text, styles):
    inner = Paragraph(text, styles["BodyText2"])
    t = Table([[inner]], colWidths=[150*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _make_table(headers, rows, col_widths=None):
    data = [headers] + rows
    if not col_widths:
        n = len(headers)
        col_widths = [150*mm / n] * n
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, PRIMARY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, BG_LIGHT]),
    ]))
    return t


def generate_pdf_report(title, content, output_filename=None, author="Kaihara OS", subtitle="", page_size="A4"):
    if not output_filename:
        safe = "".join(c if c.isalnum() or c in "-_ " else "" for c in title)
        output_filename = f"report_{safe.lower().replace(chr(32), chr(95))}"
    filepath = OUTPUT_DIR / f"{output_filename}.pdf"
    doc = KaiharaDocTemplate(str(filepath), pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=30*mm, bottomMargin=30*mm, report_title=title, author=author)
    styles = _get_styles()
    story = []
    story.append(Spacer(1, 15*mm))
    story.append(Paragraph(title, styles["ReportTitle"]))
    if subtitle:
        story.append(Paragraph(subtitle, styles["ReportSubtitle"]))
    else:
        story.append(Paragraph(f"Generated by {author} — {datetime.now().strftime('%d %B %Y %H:%M')}", styles["ReportSubtitle"]))
    story.append(_make_section_divider())
    story.append(Spacer(1, 5*mm))
    for block in content:
        bt = block.get("type", "paragraph")
        if bt == "heading":
            level = block.get("level", 2)
            text = block.get("text", "")
            if level <= 2:
                story.append(Paragraph(text, styles["SectionHeading"]))
                story.append(_make_section_divider())
            else:
                story.append(Paragraph(text, styles["SubHeading"]))
        elif bt == "paragraph":
            story.append(Paragraph(block.get("text", ""), styles["BodyText2"]))
        elif bt == "bullet":
            for item in block.get("items", []):
                story.append(Paragraph(f"<bullet>&bull;</bullet> {item}", styles["BulletItem"]))
            story.append(Spacer(1, 3*mm))
        elif bt == "table":
            headers = block.get("headers", [])
            rows = block.get("rows", [])
            if headers and rows:
                story.append(_make_table(headers, rows))
                story.append(Spacer(1, 5*mm))
        elif bt == "highlight":
            story.append(_make_highlight_box(block.get("text", ""), styles))
            story.append(Spacer(1, 4*mm))
        elif bt == "divider":
            story.append(_make_section_divider())
        elif bt == "spacer":
            story.append(Spacer(1, block.get("height", 20)))
    story.append(Spacer(1, 10*mm))
    story.append(_make_section_divider())
    story.append(Paragraph("End of Report — Ghazwah Group", styles["SmallGray"]))
    doc.build(story)
    return str(filepath)
