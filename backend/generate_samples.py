from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parent / "sample_docs"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _write_pdf(path: Path, operations: list[str]) -> None:
    stream = "\n".join(operations).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]

    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{index} 0 obj\n".encode("ascii"))
        content.extend(obj)
        content.extend(b"\nendobj\n")

    xref_offset = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    content.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    content.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(bytes(content))


def text_op(x: int, y: int, text: str, size: int = 12, bold: bool = False) -> str:
    font = "F2" if bold else "F1"
    return f"BT /{font} {size} Tf {x} {y} Td ({_escape_pdf_text(text)}) Tj ET"


def line_op(x1: int, y1: int, x2: int, y2: int) -> str:
    return f"{x1} {y1} m {x2} {y2} l S"


def create_report_pdf() -> None:
    ops = [
        text_op(72, 735, "Q3 AI Adoption Report", 18, True),
        text_op(72, 700, "Revenue grew 15 percent year over year to $1.2M.", 12),
        text_op(72, 676, "Net profit was $400k after infrastructure optimization.", 12),
        text_op(72, 652, "Key driver: enterprise customers adopted the RAG assistant package.", 12),
        text_op(72, 610, "Sensitivity: internal business report.", 12),
    ]
    _write_pdf(OUT_DIR / "q3_ai_adoption_report.pdf", ops)


def create_table_pdf() -> None:
    x0, y0 = 72, 640
    col_widths = [160, 100, 100, 100]
    row_height = 34
    rows = [
        ["Item", "Qty", "Unit Price", "Total"],
        ["AI Consulting", "1", "$5,000", "$5,000"],
        ["Server Costs", "1", "$300", "$300"],
        ["Support", "2", "$250", "$500"],
    ]
    width = sum(col_widths)
    height = row_height * len(rows)
    ops = [
        text_op(72, 735, "Invoice INV-001", 18, True),
        text_op(72, 708, "Billed To: Acme Corp", 12),
        text_op(72, 686, "Status: unpaid", 12),
    ]
    for i in range(len(rows) + 1):
        y = y0 - i * row_height
        ops.append(line_op(x0, y, x0 + width, y))
    current_x = x0
    ops.append(line_op(current_x, y0, current_x, y0 - height))
    for col_width in col_widths:
        current_x += col_width
        ops.append(line_op(current_x, y0, current_x, y0 - height))
    for row_index, row in enumerate(rows):
        current_x = x0 + 8
        y = y0 - 23 - row_index * row_height
        for col_index, value in enumerate(row):
            ops.append(text_op(current_x, y, value, 11, row_index == 0))
            current_x += col_widths[col_index]
    ops.append(text_op(72, 460, "Grand Total: $5,800", 13, True))
    _write_pdf(OUT_DIR / "invoice_with_table.pdf", ops)


def create_scanned_pdf() -> None:
    image = Image.new("RGB", (1000, 1300), "white")
    draw = ImageDraw.Draw(image)
    lines = [
        "Scanned Security Checklist",
        "1. Uploaded files must be MIME validated.",
        "2. Encrypted storage is mandatory.",
        "3. Temporary decrypted files must be deleted.",
        "4. API access requires a shared assessment key.",
    ]
    y = 110
    for line in lines:
        draw.text((90, y), line, fill=(15, 23, 42))
        y += 70
    image.save(OUT_DIR / "scanned_security_checklist.pdf", "PDF", resolution=150.0)


def create_image_doc() -> None:
    image = Image.new("RGB", (900, 700), (248, 250, 252))
    draw = ImageDraw.Draw(image)
    draw.rectangle((60, 60, 840, 640), outline=(79, 70, 229), width=4)
    draw.text((100, 120), "Image-Heavy Product Brief", fill=(15, 23, 42))
    draw.text((100, 190), "Feature: citation thumbnails open full source pages.", fill=(15, 23, 42))
    draw.text((100, 250), "Owner: Build Fast with AI assessment team.", fill=(15, 23, 42))
    draw.text((100, 310), "Sensitivity: public demo material.", fill=(15, 23, 42))
    image.save(OUT_DIR / "product_brief_image.png", "PNG")


def create_text_doc() -> None:
    (OUT_DIR / "support_notes.txt").write_text(
        "Support Notes\n"
        "The chatbot must answer only from uploaded documents.\n"
        "If the answer is not present, it should say the documents do not contain enough information.\n"
        "Voice input uses browser-native speech recognition for the assessment bonus.\n",
        encoding="utf-8",
    )


def main() -> None:
    create_report_pdf()
    create_table_pdf()
    create_scanned_pdf()
    create_image_doc()
    create_text_doc()
    for path in sorted(OUT_DIR.iterdir()):
        print(f"Generated {path.relative_to(OUT_DIR.parent)}")


if __name__ == "__main__":
    main()
