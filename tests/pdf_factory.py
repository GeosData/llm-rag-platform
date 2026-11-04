def build_pdf(page_texts: list[str]) -> bytes:
    objects: list[bytes] = []
    page_count = len(page_texts)
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(page_count))
    font_id = 3 + 2 * page_count
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode())
    for i, text in enumerate(page_texts):
        content_id = 4 + 2 * i
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
                f"/Contents {content_id} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>"
            ).encode()
        )
        stream = f"BT /F1 12 Tf 20 150 Td ({text}) Tj ET".encode()
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    output = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_position = len(output)
    output += f"xref\n0 {len(objects) + 1}\n".encode()
    output += b"0000000000 65535 f \n"
    for offset in offsets:
        output += f"{offset:010d} 00000 n \n".encode()
    output += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_position}\n%%EOF\n"
    ).encode()
    return bytes(output)
