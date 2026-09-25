import pytest

from community_view.config import PDFConfig
from community_view.ingest import ingestion_signature
from community_view.overviews import object_schema, string_schema, validate_object
from community_view.pdf import PDFParser, clean_unicode, markdown_table
from community_view.text import read_document


def make_pdf(path, *, outlines=False, blank=False):
    """Small real PDF with fonts, two pages, a ruled table and an optional bookmark."""
    content = (
        b""
        if blank
        else (
            b"BT /F1 24 Tf 50 730 Td (Introduction) Tj ET\n"
            b"BT /F1 16 Tf 50 690 Td (Methods) Tj ET\n"
            b"BT /F1 10 Tf 50 660 Td (This is body text describing the experiment in detail.) Tj ET\n"
            b"BT /F1 10 Tf 50 640 Td (More body text with enough characters for font detection.) Tj ET\n"
            b"50 450 220 60 re S 160 450 m 160 510 l S 50 480 m 270 480 l S\n"
            b"BT /F1 10 Tf 60 490 Td (Model) Tj ET\n"
            b"BT /F1 10 Tf 170 490 Td (Accuracy) Tj ET\n"
            b"BT /F1 10 Tf 60 460 Td (A) Tj ET\n"
            b"BT /F1 10 Tf 170 460 Td (0.90) Tj ET\n"
        )
    )
    second = b"" if blank else b"BT /F1 10 Tf 50 730 Td (Second page content.) Tj ET\n"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R " + (b"/Outlines 8 0 R" if outlines else b"") + b" >>",
        b"<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"endstream",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 7 0 R >>",
        f"<< /Length {len(second)} >>\nstream\n".encode() + second + b"endstream",
    ]
    if outlines:
        objects.extend(
            [
                b"<< /Type /Outlines /First 9 0 R /Last 9 0 R /Count 1 >>",
                b"<< /Title (Introduction) /Parent 8 0 R /Dest [3 0 R /Fit] >>",
            ]
        )
    data = b"%PDF-1.4\n"
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    offset = len(data)
    data += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    data += b"".join(f"{n:010d} 00000 n \n".encode() for n in offsets[1:])
    data += (
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{offset}\n%%EOF\n".encode()
    )
    path.write_bytes(data)
    return path


@pytest.mark.parametrize("outlines", [False, True])
def test_pdf_markdown_real_pages_headings_tables(tmp_path, outlines):
    source = make_pdf(tmp_path / "paper.pdf", outlines=outlines)
    text = read_document(source)
    assert text.startswith("<!-- Page 1 -->")
    assert "# Introduction" in text
    assert ("## Methods" in text) is not outlines
    assert "| Model | Accuracy |" in text
    assert "| A | 0.90 |" in text
    assert text.index("<!-- Page 2 -->") > text.index("0.90")
    assert "Second page content." in text
    text.encode("utf-8")


def test_blank_pdf_is_not_made_nonempty_by_page_markers(tmp_path):
    with pytest.raises(ValueError, match="No extractable text"):
        read_document(make_pdf(tmp_path / "blank.pdf", blank=True))


def test_table_escape_and_unicode_repair(caplog):
    assert clean_unicode("x\ud835\udc00y\ud835z", "paper page=1") == "x𝐀y�z"
    assert "restored_pairs=1 replaced_lone_surrogates=1" in caplog.text
    assert markdown_table([["A|B", "C"], [None, "x\ny"]]) == (
        "| A\\|B | C |\n| --- | --- |\n|  | x<br>y |"
    )


def test_pdf_settings_invalidate_ingestion_signature(config):
    before = ingestion_signature(config)
    config.text.pdf.extract_tables = False
    assert before != ingestion_signature(config)


def test_summary_override_does_not_relax_other_fields():
    schema = object_schema({"title": string_schema(3), "summary": string_schema(800)})
    with pytest.raises(ValueError, match="title"):
        validate_object(
            {"title": "long", "summary": "x" * 900}, schema, length_overrides={"summary": 1000}
        )


def test_heading_levels_are_bounded():
    parser = PDFParser(PDFConfig(max_heading_level=4))
    assert (
        parser._mark_headings("Intro\nBody", [(1, "Intro")], append_unmatched=True)
        == "# Intro\nBody"
    )
