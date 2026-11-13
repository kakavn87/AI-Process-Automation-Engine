from io import BytesIO

import pytest
from docx import Document
from PIL import Image

from app.services.document_service import DocumentProcessingService


def test_extracts_plain_text_and_source_metadata():
    result = DocumentProcessingService().process([
        ("inbound-process.txt", b"Receive goods, inspect quantity, and register delivery.")
    ])

    assert "inspect quantity" in result["text_context"]
    assert result["documents"][0]["filename"] == "inbound-process.txt"
    assert result["documents"][0]["fileType"] == "TXT"
    assert result["image_data_urls"] == []


def test_rejects_pdf_with_invalid_signature():
    with pytest.raises(ValueError, match="valid PDF signature"):
        DocumentProcessingService().process([("fake.pdf", b"not a pdf")])


def test_extracts_docx_paragraphs_and_tables():
    document = Document()
    document.add_paragraph("Supplier sends a delivery notification.")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Purchase order"
    table.rows[0].cells[1].text = "Delivery date"
    output = BytesIO()
    document.save(output)

    result = DocumentProcessingService().process([("process.docx", output.getvalue())])

    assert "delivery notification" in result["text_context"]
    assert "Purchase order | Delivery date" in result["text_context"]


def test_normalizes_uploaded_image_for_vision_model():
    image = Image.new("RGB", (32, 32), "white")
    output = BytesIO()
    image.save(output, format="PNG")

    result = DocumentProcessingService().process([("diagram.png", output.getvalue())])

    assert len(result["image_data_urls"]) == 1
    assert result["image_data_urls"][0].startswith("data:image/jpeg;base64,")
    assert result["documents"][0]["visualAssets"] == 1


def test_rejects_too_many_files():
    files = [(f"file-{index}.txt", b"process") for index in range(9)]

    with pytest.raises(ValueError, match="no more than 8"):
        DocumentProcessingService().process(files)
