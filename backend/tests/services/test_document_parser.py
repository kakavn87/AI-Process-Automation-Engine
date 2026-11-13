import pytest

from app.services.document_parser import extract_document, split_segments


def test_extracts_plain_text_with_document_locator():
    segments, metadata = extract_document("process.txt", b"Receive request\nValidate data\nApprove order")
    assert [item["locator"]["section"] for item in segments] == ["document"]
    assert "Validate data" in segments[0]["text"]
    assert metadata["parser"] == "txt"


def test_extracts_bpmn_tasks_and_sequence_flows():
    xml = b"""<?xml version="1.0"?>
    <definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL">
      <process id="p1" name="Purchase approval">
        <startEvent id="start" name="Request received"/>
        <task id="review" name="Manager reviews request"/>
        <exclusiveGateway id="decision" name="Budget available?"/>
        <sequenceFlow id="f1" sourceRef="start" targetRef="review"/>
      </process>
    </definitions>"""
    segments, _ = extract_document("purchase.bpmn", xml)
    text = segments[0]["text"]
    assert "Request received" in text
    assert "Manager reviews request" in text
    assert "Budget available?" in text
    assert "start -> review" in text


def test_extracts_uncompressed_drawio_labels():
    xml = b"""<mxfile><diagram name="Purchase"><mxGraphModel><root>
      <mxCell id="1" value="Purchase request"/>
      <mxCell id="2" value="Manager approval"/>
    </root></mxGraphModel></diagram></mxfile>"""
    segments, _ = extract_document("purchase.drawio", xml)
    assert "Purchase request" in segments[0]["text"]
    assert "Manager approval" in segments[0]["text"]


def test_split_segments_keeps_source_locator_and_bounds_chunk_size():
    source = {"text": ("Approval process and responsible manager. " * 100),
              "locator": {"page": 4}}
    chunks = split_segments([source], chunk_size=180, overlap=30)
    assert len(chunks) > 1
    assert all(len(item["content"]) <= 180 for item in chunks)
    assert all(item["source_locator"] == {"page": 4} for item in chunks)
    assert chunks[0]["content"][-20:] in chunks[1]["content"]


def test_rejects_unsupported_extension():
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_document("payload.exe", b"not a document")
