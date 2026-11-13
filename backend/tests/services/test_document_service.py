from io import BytesIO

import pytest
from docx import Document
from PIL import Image
from pypdf import PdfWriter

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


def test_renders_pdf_pages_for_diagram_vision():
    writer = PdfWriter()
    writer.add_blank_page(width=240, height=160)
    output = BytesIO()
    writer.write(output)

    result = DocumentProcessingService().process([("process-diagram.pdf", output.getvalue())])

    assert result["documents"][0]["pages"] == 1
    assert len(result["image_data_urls"]) == 1
    assert result["image_data_urls"][0].startswith("data:image/jpeg;base64,")


def test_extracts_drawio_nodes_and_connections():
    xml = b"""<mxfile><diagram><mxGraphModel><root>
      <mxCell id="0"/><mxCell id="1" parent="0"/>
      <mxCell id="2" value="Receive request" vertex="1" parent="1"/>
      <mxCell id="3" value="Approve request" vertex="1" parent="1"/>
      <mxCell id="4" edge="1" source="2" target="3"/>
    </root></mxGraphModel></diagram></mxfile>"""

    result = DocumentProcessingService._extract_xml_diagram("process.drawio", xml, ".drawio")

    assert "Receive request" in result
    assert "Approve request" in result
    assert "Receive request -> Approve request" in result


def test_extracts_bpmn_tasks_and_sequence_flow():
    xml = b"""<?xml version="1.0"?>
    <definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL">
      <process id="purchase">
        <startEvent id="start" name="Request received"/>
        <task id="approve" name="Manager approval"/>
        <sequenceFlow id="flow1" sourceRef="start" targetRef="approve"/>
      </process>
    </definitions>"""

    result = DocumentProcessingService._extract_xml_diagram("purchase.bpmn", xml, ".bpmn")

    assert "Request received" in result
    assert "Manager approval" in result
    assert "start -> approve" in result

def test_normalizes_uploaded_tiff_for_vision_model():
    image = Image.new("RGB", (32, 32), "white")
    output = BytesIO()
    image.save(output, format="TIFF")

    result = DocumentProcessingService().process([("diagram.tiff", output.getvalue())])

    assert len(result["image_data_urls"]) == 1
    assert result["image_data_urls"][0].startswith("data:image/jpeg;base64,")
    assert result["documents"][0]["fileType"] == "TIFF"
    assert result["documents"][0]["visualAssets"] == 1
