from app.services.knowledge_base_service import KnowledgeBaseService


def test_splits_document_context_with_source_and_page_metadata():
    document_text = (
        "[Source document: purchasing-policy.pdf]\n"
        "[Page 1]\n"
        "Purchase requests must include a cost center and the supplier name.\n"
        "[Page 2]\n"
        "Requests above the approval threshold require finance approval."
    )

    chunks = KnowledgeBaseService.split_document_context(document_text)

    assert len(chunks) == 2
    assert chunks[0]["source_file"] == "purchasing-policy.pdf"
    assert chunks[0]["page"] == 1
    assert "cost center" in chunks[0]["content"]
    assert chunks[1]["source_file"] == "purchasing-policy.pdf"
    assert chunks[1]["page"] == 2
    assert "finance approval" in chunks[1]["content"]


def test_splits_multiple_documents_without_mixing_source_metadata():
    document_text = (
        "[Source document: policy.pdf]\n"
        "[Page 4]\n"
        "Policy content.\n"
        "[Source document: workflow.drawio]\n"
        "[Draw.io diagram nodes]\n"
        "Receive request\n"
        "Approve request"
    )

    chunks = KnowledgeBaseService.split_document_context(document_text)

    assert chunks[0]["source_file"] == "policy.pdf"
    assert chunks[0]["page"] == 4
    assert chunks[1]["source_file"] == "workflow.drawio"
    assert chunks[1]["page"] is None
    assert "Approve request" in chunks[1]["content"]
