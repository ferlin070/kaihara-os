"""
PDF Generator — Create PDF documents from text, HTML, or structured data.
Supports invoices, reports, certificates, and custom documents.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

logger = logging.getLogger("kaihara.pdf_generator")

# Output directory
OUTPUT_DIR = Path(os.getenv("KAIHARA_OUTPUT_DIR", "outputs/pdfs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_pdf_report(
    title: str,
    content: list[dict],
    output_filename: Optional[str] = None,
    author: str = "Kaihara OS",
    page_size: str = "A4",
) -> str:
    """Generate a PDF report from structured content.
    
    Args:
        title: Report title
        content: List of content blocks, each with 'type' and data
                 Types: 'heading', 'paragraph', 'list', 'table', 'spacer'
        output_filename: Custom filename (without .pdf)
        author: Document author
        page_size: Page size (A4, letter)
    
    Returns:
        Path to generated PDF file
    """
    if not output_filename:
        output_filename = f"report_{title.lower().replace(' ', '_')}"
    
    filepath = OUTPUT_DIR / f"{output_filename}.pdf"
    
    # Page size
    size = A4 if page_size.upper() == "A4" else letter
    
    # Create document
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=size,
        rightMargin=25*mm,
        leftMargin=25*mm,
        topMargin=25*mm,
        bottomMargin=25*mm,
    )
    
    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=HexColor('#8b5cf6'),
    ))
    styles.add(ParagraphStyle(
        name='CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=10,
        textColor=HexColor('#1a1a1a'),
    ))
    styles.add(ParagraphStyle(
        name='CustomParagraph',
        parent=styles['Normal'],
        fontSize=11,
        spaceBefore=6,
        spaceAfter=6,
        leading=16,
    ))
    
    # Build story
    story = []
    
    # Title
    story.append(Paragraph(title, styles['CustomTitle']))
    story.append(HRFlowable(width="100%", thickness=2, color=HexColor('#8b5cf6')))
    story.append(Spacer(1, 20))
    
    # Content blocks
    for block in content:
        block_type = block.get('type', 'paragraph')
        
        if block_type == 'heading':
            level = block.get('level', 2)
            text = block.get('text', '')
            style_name = f'Heading{level}' if level <= 5 else 'Heading5'
            story.append(Paragraph(text, styles[style_name]))
            
        elif block_type == 'paragraph':
            text = block.get('text', '')
            story.append(Paragraph(text, styles['CustomParagraph']))
            
        elif block_type == 'list':
            items = block.get('items', [])
            for item in items:
                story.append(Paragraph(f"• {item}", styles['CustomParagraph']))
                
        elif block_type == 'table':
            headers = block.get('headers', [])
            rows = block.get('rows', [])
            
            data = [headers] + rows
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#8b5cf6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f5f5f5')),
                ('GRID', (0, 0), (-1, -1), 1, HexColor('#e0e0e0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f9f9f9')]),
            ]))
            story.append(table)
            story.append(Spacer(1, 12))
            
        elif block_type == 'spacer':
            height = block.get('height', 20)
            story.append(Spacer(1, height))
    
    # Build PDF
    doc.build(story)
    
    logger.info(f"PDF generated: {filepath}")
    return str(filepath)


def generate_invoice(
    invoice_number: str,
    from_name: str,
    from_address: str,
    to_name: str,
    to_address: str,
    items: list[dict],
    tax_rate: float = 0.0,
    notes: str = "",
    output_filename: Optional[str] = None,
) -> str:
    """Generate an invoice PDF.
    
    Args:
        invoice_number: Invoice number
        from_name: Sender name/company
        from_address: Sender address
        to_name: Recipient name/company
        to_address: Recipient address
        items: List of items with 'description', 'quantity', 'price'
        tax_rate: Tax rate (e.g., 0.06 for 6%)
        notes: Additional notes
        output_filename: Custom filename
    
    Returns:
        Path to generated PDF
    """
    if not output_filename:
        output_filename = f"invoice_{invoice_number}"
    
    filepath = OUTPUT_DIR / f"{output_filename}.pdf"
    
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        rightMargin=25*mm,
        leftMargin=25*mm,
        topMargin=25*mm,
        bottomMargin=25*mm,
    )
    
    styles = getSampleStyleSheet()
    
    story = []
    
    # Header
    story.append(Paragraph("INVOICE", styles['Heading1']))
    story.append(Spacer(1, 10))
    
    # Invoice info
    invoice_data = [
        ['Invoice Number:', invoice_number],
        ['Date:', 'January 2026'],
    ]
    invoice_table = Table(invoice_data, colWidths=[100, 200])
    invoice_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    story.append(invoice_table)
    story.append(Spacer(1, 20))
    
    # From/To addresses
    address_data = [
        [Paragraph(f"<b>From:</b><br/>{from_name}<br/>{from_address}", styles['Normal']),
         Paragraph(f"<b>To:</b><br/>{to_name}<br/>{to_address}", styles['Normal'])]
    ]
    address_table = Table(address_data, colWidths=[250, 250])
    story.append(address_table)
    story.append(Spacer(1, 20))
    
    # Items table
    headers = ['Description', 'Qty', 'Price', 'Total']
    rows = []
    subtotal = 0
    
    for item in items:
        qty = item.get('quantity', 1)
        price = item.get('price', 0)
        total = qty * price
        subtotal += total
        rows.append([
            item.get('description', ''),
            str(qty),
            f"RM {price:.2f}",
            f"RM {total:.2f}"
        ])
    
    # Add subtotal, tax, total
    tax = subtotal * tax_rate
    grand_total = subtotal + tax
    
    rows.append(['', '', 'Subtotal:', f"RM {subtotal:.2f}"])
    if tax_rate > 0:
        rows.append(['', '', f'Tax ({tax_rate*100:.0f}%):', f"RM {tax:.2f}"])
    rows.append(['', '', 'Total:', f"RM {grand_total:.2f}"])
    
    items_table = Table([headers] + rows, colWidths=[200, 60, 100, 100])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#8b5cf6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, len(items)), 1, HexColor('#e0e0e0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, len(items)), [white, HexColor('#f9f9f9')]),
        ('LINEBELOW', (0, -1), (-1, -1), 2, HexColor('#8b5cf6')),
    ]))
    story.append(items_table)
    
    # Notes
    if notes:
        story.append(Spacer(1, 20))
        story.append(Paragraph(f"<b>Notes:</b> {notes}", styles['Normal']))
    
    # Footer
    story.append(Spacer(1, 40))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#e0e0e0')))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Generated by Kaihara OS", styles['Normal']))
    
    doc.build(story)
    
    logger.info(f"Invoice generated: {filepath}")
    return str(filepath)


def generate_certificate(
    recipient_name: str,
    certificate_title: str,
    description: str,
    issue_date: str,
    issuer_name: str = "Kaihara OS",
    output_filename: Optional[str] = None,
) -> str:
    """Generate a certificate PDF.
    
    Args:
        recipient_name: Name of the recipient
        certificate_title: Title of the certificate
        description: Description of achievement
        issue_date: Date of issue
        issuer_name: Name of issuing organization
        output_filename: Custom filename
    
    Returns:
        Path to generated PDF
    """
    if not output_filename:
        output_filename = f"certificate_{recipient_name.lower().replace(' ', '_')}"
    
    filepath = OUTPUT_DIR / f"{output_filename}.pdf"
    
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=letter,
        rightMargin=1*inch,
        leftMargin=1*inch,
        topMargin=1*inch,
        bottomMargin=1*inch,
    )
    
    styles = getSampleStyleSheet()
    
    story = []
    
    # Border decoration
    story.append(Spacer(1, 50))
    
    # Title
    story.append(Paragraph("CERTIFICATE", styles['Title']))
    story.append(Spacer(1, 20))
    
    # Subtitle
    story.append(Paragraph(certificate_title, styles['Heading2']))
    story.append(Spacer(1, 30))
    
    # Recipient
    story.append(Paragraph("This is to certify that", styles['Normal']))
    story.append(Spacer(1, 10))
    story.append(Paragraph(recipient_name, styles['Heading1']))
    story.append(Spacer(1, 20))
    
    # Description
    story.append(Paragraph(description, styles['Normal']))
    story.append(Spacer(1, 40))
    
    # Date and issuer
    story.append(Paragraph(f"Issued on: {issue_date}", styles['Normal']))
    story.append(Spacer(1, 10))
    story.append(Paragraph(issuer_name, styles['Normal']))
    
    doc.build(story)
    
    logger.info(f"Certificate generated: {filepath}")
    return str(filepath)


def generate_text_pdf(
    text: str,
    output_filename: Optional[str] = None,
    title: Optional[str] = None,
) -> str:
    """Generate a simple PDF from text content.
    
    Args:
        text: Plain text content
        output_filename: Custom filename
        title: Optional title
    
    Returns:
        Path to generated PDF
    """
    if not output_filename:
        output_filename = "document"
    
    filepath = OUTPUT_DIR / f"{output_filename}.pdf"
    
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        rightMargin=25*mm,
        leftMargin=25*mm,
        topMargin=25*mm,
        bottomMargin=25*mm,
    )
    
    styles = getSampleStyleSheet()
    
    story = []
    
    if title:
        story.append(Paragraph(title, styles['Title']))
        story.append(Spacer(1, 20))
    
    # Split text into paragraphs
    paragraphs = text.split('\n\n')
    for para in paragraphs:
        if para.strip():
            story.append(Paragraph(para.strip(), styles['Normal']))
            story.append(Spacer(1, 12))
    
    doc.build(story)
    
    logger.info(f"Text PDF generated: {filepath}")
    return str(filepath)


# Tool registration for Kaihara
TOOLS = {
    "generate_pdf_report": generate_pdf_report,
    "generate_invoice": generate_invoice,
    "generate_certificate": generate_certificate,
    "generate_text_pdf": generate_text_pdf,
}
