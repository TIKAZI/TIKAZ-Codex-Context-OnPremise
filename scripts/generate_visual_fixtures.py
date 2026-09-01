from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 1280, 720
BLUE = "#60A5FA"
PURPLE = "#A78BFA"
INK = "#111827"
MUTED = "#6B7280"
PAPER = "#F8FAFC"


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    raise FileNotFoundError("a Unicode TrueType font is required")


def _canvas(title: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 14), fill=BLUE)
    draw.text((64, 44), title, font=_font(34, bold=True), fill=INK)
    return image, draw


def _save(image: Image.Image, output: Path, name: str) -> None:
    image.save(output / name, format="PNG", optimize=True)


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)

    image, draw = _canvas("Release verification")
    for y, text in enumerate(("Version  v4.8.0", "Date     2026-08-20", "Record   DOC-4820"), start=0):
        draw.text((100, 180 + y * 100), text, font=_font(42), fill=INK)
    _save(image, output, "01-document-release.png")

    image, draw = _canvas("发布审核记录")
    for y, text in enumerate(("版本：V3.6.1", "审核状态：通过", "工单：CN-731"), start=0):
        draw.text((100, 180 + y * 100), text, font=_font(42), fill=INK)
    _save(image, output, "02-document-zh.png")

    image, draw = _canvas("Token Forge Settings")
    rows = (("Security mode", "Strict"), ("API endpoint", "Local only"), ("Build", "2026.8"))
    for index, (label, value) in enumerate(rows):
        y = 160 + index * 120
        draw.text((90, y), label, font=_font(30), fill=MUTED)
        draw.rounded_rectangle((700, y - 12, 1130, y + 62), radius=8, fill="white", outline="#CBD5E1", width=2)
        draw.text((730, y), value, font=_font(30, bold=True), fill=INK)
    _save(image, output, "03-ui-settings.png")

    image, draw = _canvas("Acceptance Dashboard")
    cards = (("Weighted reduction", "89.57%"), ("Macro average", "55.96%"), ("Unit tests", "80/80"))
    for index, (label, value) in enumerate(cards):
        x = 65 + index * 400
        draw.rounded_rectangle((x, 160, x + 350, 440), radius=8, fill="white", outline="#E2E8F0", width=2)
        draw.text((x + 28, 205), label, font=_font(25), fill=MUTED)
        draw.text((x + 28, 300), value, font=_font(54, bold=True), fill=BLUE if index != 1 else PURPLE)
    _save(image, output, "04-ui-dashboard.png")

    image, draw = _canvas("Plan comparison")
    table = (("Plan", "Monthly", "Seats"), ("Basic", "$9", "1"), ("Pro", "$29", "5"), ("Team", "$79", "20"))
    for row, values in enumerate(table):
        y = 150 + row * 95
        draw.rectangle((90, y, 1190, y + 95), fill="white" if row else "#DBEAFE", outline="#CBD5E1", width=2)
        for column, value in enumerate(values):
            draw.text((125 + column * 360, y + 25), value, font=_font(28, bold=row == 0), fill=INK)
    _save(image, output, "05-table-pricing.png")

    image, draw = _canvas("Visual fact recall")
    values = (("OCR 42", 42, "#94A3B8"), ("VLM 68", 68, PURPLE), ("Hybrid 91", 91, BLUE))
    for index, (label, value, color) in enumerate(values):
        x = 170 + index * 330
        draw.rectangle((x, 590 - value * 4, x + 180, 590), fill=color)
        draw.text((x, 610), label, font=_font(28, bold=True), fill=INK)
    _save(image, output, "06-chart-bars.png")

    image, draw = _canvas("Evidence routing")
    labels = ("Input", "OCR", "VLM", "Codex Review")
    for index, label in enumerate(labels):
        x = 55 + index * 305
        draw.rounded_rectangle((x, 270, x + 230, 390), radius=8, fill="white", outline=BLUE, width=4)
        draw.text((x + 28, 305), label, font=_font(27, bold=True), fill=INK)
        if index < len(labels) - 1:
            draw.line((x + 230, 330, x + 290, 330), fill=PURPLE, width=6)
            draw.polygon(((x + 290, 330), (x + 270, 318), (x + 270, 342)), fill=PURPLE)
    _save(image, output, "07-diagram-flow.png")

    image, draw = _canvas("Spatial relation")
    draw.rectangle((180, 240, 440, 500), fill=BLUE)
    draw.ellipse((820, 240, 1080, 500), fill=PURPLE)
    draw.text((205, 525), "Blue square", font=_font(28, bold=True), fill=INK)
    draw.text((850, 525), "Purple circle", font=_font(28, bold=True), fill=INK)
    draw.text((540, 345), "LEFT OF", font=_font(34, bold=True), fill=INK)
    _save(image, output, "08-spatial-shapes.png")

    image, draw = _canvas("Validation blocked")
    draw.rounded_rectangle((230, 150, 1050, 590), radius=8, fill="white", outline="#EF4444", width=4)
    draw.text((300, 220), "Blocked", font=_font(48, bold=True), fill="#B91C1C")
    draw.text((300, 330), "Error code: TF-409", font=_font(34), fill=INK)
    draw.rounded_rectangle((300, 450, 650, 530), radius=8, fill=BLUE)
    draw.text((355, 467), "Review source", font=_font(28, bold=True), fill="white")
    _save(image, output, "09-warning-dialog.png")

    image, draw = _canvas("Invoice INV-9401")
    draw.text((90, 170), "Invoice number", font=_font(27), fill=MUTED)
    draw.text((430, 170), "INV-9401", font=_font(31, bold=True), fill=INK)
    draw.text((90, 280), "Total", font=_font(27), fill=MUTED)
    draw.text((430, 280), "188000.50", font=_font(40, bold=True), fill=BLUE)
    draw.text((90, 410), "Due date", font=_font(27), fill=MUTED)
    draw.text((430, 410), "2026-12-21", font=_font(31, bold=True), fill=INK)
    _save(image, output, "10-invoice.png")

    image, draw = _canvas("Local pipeline timing")
    draw.line((150, 350, 1130, 350), fill="#94A3B8", width=5)
    for index, text in enumerate(("Extract 2.1s", "OCR 5.4s", "VLM 12.8s")):
        x = 220 + index * 390
        draw.ellipse((x - 20, 330, x + 20, 370), fill=BLUE if index != 1 else PURPLE)
        draw.text((x - 80, 410), text, font=_font(27, bold=True), fill=INK)
    _save(image, output, "11-timeline.png")

    image, draw = _canvas("Warehouse observation")
    draw.rectangle((70, 150, 1210, 620), fill="#E5E7EB", outline="#94A3B8", width=4)
    draw.text((95, 175), "Dock 7", font=_font(34, bold=True), fill=INK)
    draw.rectangle((840, 230, 1130, 560), fill="#CBD5E1", outline=INK, width=4)
    draw.text((915, 255), "Bay C", font=_font(32, bold=True), fill=INK)
    for index in range(3):
        x = 180 + index * 190
        draw.rectangle((x, 410, x + 135, 530), fill="#D97706", outline="#92400E", width=3)
    draw.text((240, 555), "3 pallets", font=_font(30, bold=True), fill=INK)
    _save(image, output, "12-warehouse-scene.png")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    generate(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
