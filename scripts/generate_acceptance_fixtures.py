from __future__ import annotations

import json
import zipfile
from pathlib import Path

from docx import Document
from openpyxl import Workbook
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas


ROOT = Path(__file__).resolve().parents[1] / "benchmarks" / "acceptance-fixtures"


def make_docx() -> None:
    document = Document()
    document.add_heading("TIKAZ Token Forge Office Acceptance", level=1)
    document.add_paragraph("Release v9.4.0 is scheduled for 2026-12-21.")
    table = document.add_table(rows=2, cols=3)
    for cell, value in zip(
        table.rows[0].cells + table.rows[1].cells,
        ("Item", "Amount", "Approval", "OFFICE-940", "188000.50", "APPROVED_TIKAZ_94"),
    ):
        cell.text = value
    document.save(ROOT / "office.docx")
    (ROOT / "office-reference.txt").write_text(
        "TIKAZ Token Forge Office Acceptance Release v9.4.0 is scheduled for 2026-12-21. "
        "Item Amount Approval OFFICE-940 188000.50 APPROVED_TIKAZ_94",
        encoding="utf-8",
    )


def make_pptx() -> None:
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide.shapes.title.text = "TIKAZ Token Forge Presentation"
    slide.placeholders[1].text = "PPT_ANCHOR_940\nRelease v9.4.0\nDate 2026-12-21"
    slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide.shapes.title.text = "Safety Gate"
    slide.placeholders[1].text = "Never rewrite command: python release.py --version v9.4.0"
    presentation.save(ROOT / "slides.pptx")


def make_xlsx() -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Acceptance"
    rows = [
        ("Invoice", "Amount", "Due"),
        ("XLSX-9401", 188000.50, "2026-12-21"),
        ("XLSX-9402", 42000.25, "2027-01-10"),
    ]
    for row in rows:
        sheet.append(row)
    sheet["B2"].number_format = "0.00"
    sheet["B3"].number_format = "0.00"
    workbook.save(ROOT / "table.xlsx")


def make_pdf() -> None:
    canvas = Canvas(str(ROOT / "born-digital.pdf"), pagesize=A4)
    canvas.setTitle("TIKAZ Token Forge PDF Acceptance")
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(72, 790, "TIKAZ Token Forge PDF Acceptance")
    canvas.setFont("Helvetica", 12)
    lines = [
        "PDF_ANCHOR_940",
        "Release version: v9.4.0",
        "Migration date: 2026-12-21",
        "Command: python migrate.py --target v9.4.0",
    ]
    for index, line in enumerate(lines):
        canvas.drawString(72, 750 - index * 24, line)
    canvas.save()


def make_scan() -> None:
    image = Image.new("RGB", (1800, 1200), "white")
    draw = ImageDraw.Draw(image)
    font_path = Path("C:/Windows/Fonts/segoeui.ttf")
    bold_path = Path("C:/Windows/Fonts/seguisb.ttf")
    title_font = ImageFont.truetype(str(bold_path if bold_path.is_file() else font_path), 62)
    body_font = ImageFont.truetype(str(font_path), 42)
    draw.text((100, 100), "TIKAZ OCR Acceptance", font=title_font, fill="black")
    lines = [
        "OCR_ANCHOR_940",
        "Release version v9.4.0",
        "Verification date 2026-12-21",
        "Invoice OCR-9401 amount 188000.50",
    ]
    for index, line in enumerate(lines):
        draw.text((100, 240 + index * 100), line, font=body_font, fill="black")
    image.save(ROOT / "scan.png", dpi=(200, 200))
    image.save(ROOT / "scan.pdf", "PDF", resolution=200.0)
    (ROOT / "scan-reference.txt").write_text(
        "TIKAZ OCR Acceptance OCR_ANCHOR_940 Release version v9.4.0 "
        "Verification date 2026-12-21 Invoice OCR-9401 amount 188000.50",
        encoding="utf-8",
    )


def make_web() -> None:
    (ROOT / "dynamic-page.html").write_text(
        """<!doctype html><html><head><meta charset=\"utf-8\"><title>TIKAZ Web Acceptance</title></head>
<body><nav>Decorative navigation</nav><main id=\"content\"><h1>TIKAZ Dynamic Web</h1></main>
<script>document.getElementById('content').insertAdjacentHTML('beforeend',
'<p>WEB_ANCHOR_940</p><p>Release v9.4.0 on 2026-12-21.</p>');</script></body></html>""",
        encoding="utf-8",
    )


def make_optional_formats() -> None:
    (ROOT / "message.eml").write_text(
        "From: benchmark@example.invalid\nTo: tikaz@example.invalid\n"
        "Subject: TIKAZ acceptance EMAIL_ANCHOR_940\n\nRelease v9.4.0.",
        encoding="utf-8",
    )
    with zipfile.ZipFile(ROOT / "archive.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", "ARCHIVE_ANCHOR_940 release v9.4.0")
    with zipfile.ZipFile(ROOT / "ebook.epub", "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr(
            "META-INF/container.xml",
            "<?xml version='1.0'?><container xmlns='urn:oasis:names:tc:opendocument:xmlns:container' version='1.0'>"
            "<rootfiles><rootfile full-path='OEBPS/content.opf' media-type='application/oebps-package+xml'/></rootfiles></container>",
        )
        archive.writestr(
            "OEBPS/content.opf",
            "<?xml version='1.0'?><package xmlns='http://www.idpf.org/2007/opf' version='3.0' unique-identifier='id'>"
            "<metadata xmlns:dc='http://purl.org/dc/elements/1.1/'><dc:identifier id='id'>tikaz-940</dc:identifier>"
            "<dc:title>TIKAZ Acceptance</dc:title><dc:language>en</dc:language></metadata>"
            "<manifest><item id='chapter' href='chapter.xhtml' media-type='application/xhtml+xml'/></manifest>"
            "<spine><itemref idref='chapter'/></spine></package>",
        )
        archive.writestr(
            "OEBPS/chapter.xhtml",
            "<html xmlns='http://www.w3.org/1999/xhtml'><body><h1>EPUB_ANCHOR_940</h1><p>Release v9.4.0.</p></body></html>",
        )


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    make_docx()
    make_pptx()
    make_xlsx()
    make_pdf()
    make_scan()
    make_web()
    make_optional_formats()
    inventory = {
        path.name: {"bytes": path.stat().st_size}
        for path in sorted(ROOT.iterdir()) if path.is_file() and path.name != "fixture-inventory.json"
    }
    (ROOT / "fixture-inventory.json").write_text(
        json.dumps(inventory, indent=2, sort_keys=True), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
