import base64
import csv
import io
import re
import zlib
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import BadZipFile, ZipFile

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".pptx", ".csv", ".txt", ".md",
    ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".drawio", ".bpmn", ".xml",
}
MAX_UNCOMPRESSED_BYTES = 120 * 1024 * 1024


def _clean_text(value: str) -> str:
    value = value.replace("\x00", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _check_archive(content: bytes) -> None:
    try:
        with ZipFile(io.BytesIO(content)) as archive:
            total = 0
            if len(archive.infolist()) > 600:
                raise ValueError("The document archive contains too many entries.")
            for item in archive.infolist():
                total += item.file_size
                if total > MAX_UNCOMPRESSED_BYTES:
                    raise ValueError("The expanded document is too large to process safely.")
    except BadZipFile as exc:
        raise ValueError("The Office document is not a valid ZIP-based file.") from exc


def _extract_xml_diagram(content: bytes, suffix: str) -> list[dict]:
    raw = content.decode("utf-8-sig", errors="replace")
    if "<!DOCTYPE" in raw.upper() or "<!ENTITY" in raw.upper():
        raise ValueError("XML documents with DTD/entity declarations are not supported.")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError("Could not read this XML/diagram file.") from exc

    def labels_from(element):
        labels = []
        for item in element.iter():
            tag = item.tag.rsplit("}", 1)[-1]
            value = item.attrib.get("value") or item.attrib.get("name") or item.attrib.get("label")
            if value and value.strip():
                labels.append(f"{tag}: {value.strip()}")
            source = item.attrib.get("sourceRef") or item.attrib.get("source")
            target = item.attrib.get("targetRef") or item.attrib.get("target")
            if source and target:
                labels.append(f"Connection: {source} -> {target}")
        return list(dict.fromkeys(labels))

    labels = labels_from(root)
    # Compressed Draw.io XML is valid XML too; its visible labels are in a deflated diagram payload.
    # Try decoding every non-empty diagram payload; the wrapper title is not the diagram content.
    if suffix == ".drawio":
        for diagram in root.findall(".//diagram"):
            encoded = (diagram.text or "").strip()
            if not encoded:
                continue
            try:
                compressed = base64.b64decode(encoded)
                try:
                    decoded = zlib.decompress(compressed, -15).decode("utf-8", errors="replace")
                except zlib.error:
                    decoded = zlib.decompress(compressed).decode("utf-8", errors="replace")
                if "<!DOCTYPE" in decoded.upper() or "<!ENTITY" in decoded.upper():
                    continue
                nested = ET.fromstring(decoded)
                decoded_labels = labels_from(nested)
                if decoded_labels:
                    labels = decoded_labels
                    return [{
                        "text": f"Diagram labels and links ({suffix}):\n" + "\n".join(labels[:600]),
                        "locator": {"diagram": diagram.attrib.get("name", "Diagram")},
                    }]
            except Exception:
                continue

    if not labels:
        labels = [f"XML element: {item.tag.rsplit('}', 1)[-1]}" for item in root.iter()][:250]
    return [{
        "text": f"Diagram / BPMN structure ({suffix}):\n" + "\n".join(labels[:600]),
        "locator": {"diagram": root.attrib.get("name", "Diagram")},
    }]

def _ocr_image(content: bytes) -> str:
    from PIL import Image
    import pytesseract
    with Image.open(io.BytesIO(content)) as image:
        try:
            return pytesseract.image_to_string(image, lang="deu+eng")
        except Exception:
            return pytesseract.image_to_string(image, lang="eng")


def extract_document(filename: str, content: bytes, mime_type: str = "") -> tuple[list[dict], dict]:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix or 'unknown'}.")
    if not content:
        raise ValueError("The uploaded file is empty.")
    segments: list[dict] = []
    details: dict = {"parser": suffix.lstrip("."), "ocrUsed": False, "visionUsed": False}

    if suffix in {".txt", ".md"}:
        segments.append({"text": content.decode("utf-8-sig", errors="replace"), "locator": {"section": "document"}})
    elif suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content), strict=False)
        pdfium_document = None
        pytesseract_module = None
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = _clean_text(page.extract_text() or "")
            if page_text:
                segments.append({"text": page_text, "locator": {"page": page_number}})
                continue
            # Mixed PDFs can contain both born-digital and scanned pages. OCR only the blank pages.
            try:
                if pdfium_document is None:
                    import pypdfium2 as pdfium
                    import pytesseract
                    pdfium_document = pdfium.PdfDocument(content)
                    pytesseract_module = pytesseract
                if page_number <= min(len(pdfium_document), 20):
                    image = pdfium_document[page_number - 1].render(scale=1.6).to_pil()
                    try:
                        scanned_text = pytesseract_module.image_to_string(image, lang="deu+eng")
                    except Exception:
                        scanned_text = pytesseract_module.image_to_string(image, lang="eng")
                    scanned_text = _clean_text(scanned_text)
                    if scanned_text:
                        segments.append({"text": scanned_text, "locator": {"page": page_number, "method": "ocr"}})
                        details["ocrUsed"] = True
            except Exception:
                # OCR remains optional; retain any native PDF text already extracted.
                continue
    elif suffix == ".docx":
        _check_archive(content)
        from docx import Document
        doc = Document(io.BytesIO(content))
        for index, paragraph in enumerate(doc.paragraphs, start=1):
            value = _clean_text(paragraph.text or "")
            if value:
                segments.append({"text": value, "locator": {"paragraph": index}})
        for table_index, table in enumerate(doc.tables, start=1):
            for row_index, row in enumerate(table.rows, start=1):
                value = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if value:
                    segments.append({"text": value, "locator": {"table": table_index, "row": row_index}})
    elif suffix == ".pptx":
        _check_archive(content)
        from pptx import Presentation
        presentation = Presentation(io.BytesIO(content))
        for slide_number, slide in enumerate(presentation.slides, start=1):
            for shape_index, shape in enumerate(slide.shapes, start=1):
                if getattr(shape, "has_text_frame", False):
                    value = _clean_text(shape.text or "")
                    if value:
                        segments.append({"text": value, "locator": {"slide": slide_number, "shape": shape_index}})
                if getattr(shape, "has_table", False):
                    for row_index, row in enumerate(shape.table.rows, start=1):
                        value = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                        if value:
                            segments.append({"text": value, "locator": {"slide": slide_number, "tableRow": row_index}})
    elif suffix == ".xlsx":
        _check_archive(content)
        from openpyxl import load_workbook
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        try:
            for worksheet in workbook.worksheets:
                for row_number, row in enumerate(worksheet.iter_rows(values_only=True), start=1):
                    values = [str(value).strip() for value in row if value is not None and str(value).strip()]
                    if values:
                        segments.append({"text": " | ".join(values), "locator": {"sheet": worksheet.title, "row": row_number}})
        finally:
            workbook.close()
    elif suffix == ".csv":
        decoded = content.decode("utf-8-sig", errors="replace")
        try:
            dialect = csv.Sniffer().sniff(decoded[:4096], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        for row_number, row in enumerate(csv.reader(io.StringIO(decoded), dialect), start=1):
            values = [value.strip() for value in row if value and value.strip()]
            if values:
                segments.append({"text": " | ".join(values), "locator": {"row": row_number}})
    elif suffix in {".drawio", ".bpmn", ".xml"}:
        segments.extend(_extract_xml_diagram(content, suffix))
    else:
        try:
            text = _ocr_image(content)
            if text.strip():
                segments.append({"text": text, "locator": {"image": filename, "method": "ocr"}})
                details["ocrUsed"] = True
        except Exception:
            pass

    segments = [
        {"text": _clean_text(item["text"]), "locator": item.get("locator", {})}
        for item in segments if _clean_text(item.get("text", ""))
    ]
    if not segments:
        raise ValueError(
            "No readable text or diagram labels were found. For scanned PDFs/images, enable Tesseract OCR "
            "or configure a vision-capable model in LiteLLM."
        )
    details["segmentCount"] = len(segments)
    details["characterCount"] = sum(len(item["text"]) for item in segments)
    return segments, details


def split_segments(segments: list[dict], chunk_size: int = 1200, overlap: int = 180) -> list[dict]:
    chunks = []
    for segment in segments:
        value = segment["text"].strip()
        start = 0
        while start < len(value):
            end = min(len(value), start + chunk_size)
            if end < len(value):
                boundary = max(value.rfind("\n", start, end), value.rfind(". ", start, end))
                if boundary > start + chunk_size // 2:
                    end = boundary + 1
            content = value[start:end].strip()
            if content:
                chunks.append({"content": content, "source_locator": dict(segment.get("locator", {}))})
            if end >= len(value):
                break
            start = max(end - overlap, start + 1)
    return chunks
