from __future__ import annotations

import base64
import io
import zipfile
import re
import zlib
from html import unescape
from pathlib import PurePath
from typing import Any
from urllib.parse import unquote

from defusedxml import ElementTree as SafeET

import pypdfium2 as pdfium
from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook
from PIL import Image, ImageOps
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE


MAX_FILES = 8
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 25 * 1024 * 1024
MAX_CONTEXT_CHARS = 32_000
MAX_FILE_TEXT_CHARS = 14_000
MAX_IMAGES = 8
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 80 * 1024 * 1024
SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".txt", ".md",
    ".png", ".jpg", ".jpeg", ".webp", ".drawio", ".bpmn", ".xml",
}


class DocumentProcessingService:
    """Extract transient business-process context from uploaded documents.

    Files are processed in memory only. They are not persisted by this service.
    Raster images and rendered PDF/slide pages are passed to a vision-capable
    model as data URLs; extracted text is supplied as contextual evidence.
    """

    def process(self, files: list[tuple[str, bytes]]) -> dict[str, Any]:
        if not files:
            raise ValueError("Upload at least one document or image.")
        if len(files) > MAX_FILES:
            raise ValueError(f"Upload no more than {MAX_FILES} files at once.")

        total_size = sum(len(content) for _, content in files)
        if total_size > MAX_TOTAL_BYTES:
            raise ValueError("The combined upload size exceeds 25 MB.")

        text_sections: list[str] = []
        image_data_urls: list[str] = []
        documents: list[dict[str, Any]] = []
        warnings: list[str] = []

        for filename, content in files:
            if not filename or not content:
                raise ValueError("An uploaded file is empty or has no filename.")
            if len(content) > MAX_FILE_BYTES:
                raise ValueError(f"{filename}: each file must be 10 MB or smaller.")

            suffix = PurePath(filename).suffix.lower()
            if suffix not in SUPPORTED_EXTENSIONS:
                raise ValueError(
                    f"{filename}: unsupported file type. Supported formats: PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, PNG, JPG and WEBP."
                )

            self._validate_file_signature(filename, suffix, content)
            extracted_text = ""
            page_count: int | None = None
            visual_count_before = len(image_data_urls)

            if suffix == ".pdf":
                extracted_text, page_count = self._extract_pdf(filename, content, image_data_urls)
            elif suffix == ".docx":
                extracted_text = self._extract_docx(content)
            elif suffix == ".pptx":
                extracted_text = self._extract_pptx(content, image_data_urls)
            elif suffix == ".xlsx":
                extracted_text = self._extract_xlsx(content)
            elif suffix in {".drawio", ".bpmn", ".xml"}:
                extracted_text = self._extract_xml_diagram(filename, content, suffix)
            elif suffix in {".csv", ".txt", ".md"}:
                extracted_text = self._decode_text(content)
            else:
                self._append_image(filename, content, image_data_urls)

            extracted_text = extracted_text[:MAX_FILE_TEXT_CHARS]
            if extracted_text.strip():
                text_sections.append(f"[Source document: {filename}]\n{extracted_text.strip()}")

            visual_assets = len(image_data_urls) - visual_count_before
            documents.append({
                "filename": filename[:200],
                "fileType": suffix.lstrip(".").upper(),
                "extractedCharacters": len(extracted_text),
                "pages": page_count,
                "visualAssets": visual_assets,
            })
            if not extracted_text.strip() and visual_assets == 0:
                warnings.append(f"{filename}: no readable text or visual content could be extracted.")

        context = "\n\n".join(text_sections)[:MAX_CONTEXT_CHARS]
        if image_data_urls and not context:
            warnings.append(
                "The upload contains visual content only. A configured vision-capable AI model is required to interpret it."
            )
        if not image_data_urls and not context:
            raise ValueError("No readable content could be extracted from the uploaded files.")

        return {
            "text_context": context,
            "image_data_urls": image_data_urls[:MAX_IMAGES],
            "documents": documents,
            "warnings": warnings,
        }

    @staticmethod
    def _validate_file_signature(filename: str, suffix: str, content: bytes) -> None:
        if suffix == ".pdf" and not content.startswith(b"%PDF-"):
            raise ValueError(f"{filename}: the file does not have a valid PDF signature.")
        if suffix in {".docx", ".pptx", ".xlsx"}:
            if not zipfile.is_zipfile(io.BytesIO(content)):
                raise ValueError(f"{filename}: the Office document is invalid.")
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as archive:
                    members = archive.infolist()
                    if len(members) > 2_000 or sum(item.file_size for item in members) > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                        raise ValueError(f"{filename}: the expanded Office document is too large.")
                    names = {item.filename for item in members}
                    required = {
                        ".docx": "word/document.xml",
                        ".pptx": "ppt/presentation.xml",
                        ".xlsx": "xl/workbook.xml",
                    }[suffix]
                    if required not in names:
                        raise ValueError(f"{filename}: the Office document structure is invalid.")
            except zipfile.BadZipFile as error:
                raise ValueError(f"{filename}: the Office document is invalid.") from error
        if suffix == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError(f"{filename}: the PNG image is invalid.")
        if suffix in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8\xff"):
            raise ValueError(f"{filename}: the JPEG image is invalid.")
        if suffix == ".webp" and not (content.startswith(b"RIFF") and content[8:12] == b"WEBP"):
            raise ValueError(f"{filename}: the WEBP image is invalid.")

    @staticmethod
    def _decode_text(content: bytes) -> str:
        try:
            return content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                return content.decode("cp1252")
            except UnicodeDecodeError as error:
                raise ValueError("A text file could not be decoded as UTF-8 or Windows-1252.") from error

    def _extract_pdf(self, filename: str, content: bytes, images: list[str]) -> tuple[str, int]:
        sections: list[str] = []
        reader = PdfReader(io.BytesIO(content), strict=False)
        page_count = len(reader.pages)
        if page_count > 200:
            raise ValueError(f"{filename}: PDFs may contain no more than 200 pages.")

        # Render the first pages to capture vector flowcharts, then prioritize
        # later image-only/sparse pages. This keeps visual token usage bounded.
        visual_indices: set[int] = set(range(min(page_count, 4)))
        for index, page in enumerate(reader.pages):
            try:
                resources = page.get("/Resources")
                resources = resources.get_object() if resources else {}
                xobjects = resources.get("/XObject") if resources else None
                xobjects = xobjects.get_object() if xobjects else {}
                if any(
                    item.get_object().get("/Subtype") == "/Image"
                    for item in xobjects.values()
                ):
                    visual_indices.add(index)
            except Exception:
                # Page text remains useful even when optional image metadata is unusual.
                pass

        pdf = None
        try:
            pdf = pdfium.PdfDocument(content)
            for index, page in enumerate(reader.pages):
                page_text = (page.extract_text() or "").strip()
                if page_text:
                    sections.append(f"[Page {index + 1}]\n{page_text}")

                needs_render = (
                    index in visual_indices
                    or not page_text
                    or len(page_text) < 160
                )
                if not needs_render or len(images) >= MAX_IMAGES:
                    continue

                pdf_page = None
                bitmap = None
                try:
                    pdf_page = pdf[index]
                    bitmap = pdf_page.render(scale=1.35)
                    rendered = bitmap.to_pil()
                    output = io.BytesIO()
                    rendered.save(output, format="PNG")
                    self._append_image(
                        f"{filename} · page {index + 1}",
                        output.getvalue(),
                        images,
                    )
                finally:
                    if bitmap is not None:
                        bitmap.close()
                    if pdf_page is not None:
                        pdf_page.close()
        except ValueError:
            raise
        except Exception as error:
            raise ValueError(f"{filename}: the PDF could not be read or rendered.") from error
        finally:
            if pdf is not None:
                pdf.close()

        return "\n\n".join(sections), page_count


    @staticmethod
    def _extract_xml_diagram(filename: str, content: bytes, suffix: str) -> str:
        """Extract labels and flow edges from Draw.io, BPMN, SVG and XML diagrams."""
        try:
            xml_text = content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ValueError(f"{filename}: the XML diagram must be UTF-8 encoded.") from error

        try:
            root = SafeET.fromstring(xml_text)
        except Exception as first_error:
            root = None
            if suffix == ".drawio":
                match = re.search(r"<diagram(?:\s[^>]*)?>(.*?)</diagram>", xml_text, re.DOTALL)
                if match:
                    try:
                        compressed = base64.b64decode(match.group(1).strip(), validate=True)
                        expanded = zlib.decompress(compressed, -15)
                        decoded_xml = unquote(expanded.decode("utf-8"))
                        root = SafeET.fromstring(decoded_xml)
                    except Exception as error:
                        raise ValueError(f"{filename}: the compressed Draw.io diagram could not be decoded.") from error
            if root is None:
                raise ValueError(f"{filename}: the XML diagram is invalid.") from first_error

        if suffix == ".drawio":
            cells = [
                element for element in root.iter()
                if element.tag.rsplit("}", 1)[-1] == "mxCell"
            ]
            # Draw.io compressed files are valid outer XML, but hold the actual
            # diagram in base64/raw-DEFLATE text inside the diagram element.
            if not cells:
                diagram = next(
                    (element for element in root.iter()
                     if element.tag.rsplit("}", 1)[-1] == "diagram" and element.text),
                    None,
                )
                if diagram is not None:
                    try:
                        compressed = base64.b64decode(diagram.text.strip(), validate=True)
                        expanded = zlib.decompress(compressed, -15)
                        decoded_xml = unquote(expanded.decode("utf-8"))
                        root = SafeET.fromstring(decoded_xml)
                        cells = [
                            element for element in root.iter()
                            if element.tag.rsplit("}", 1)[-1] == "mxCell"
                        ]
                    except Exception as error:
                        raise ValueError(f"{filename}: the compressed Draw.io diagram could not be decoded.") from error

            labels: dict[str, str] = {}
            edges: list[str] = []
            for cell in cells:
                cell_id = cell.attrib.get("id", "")
                value = unescape(re.sub(r"<[^>]+>", " ", cell.attrib.get("value", ""))).strip()
                if cell_id and value:
                    labels[cell_id] = " ".join(value.split())
            for cell in cells:
                source = cell.attrib.get("source")
                target = cell.attrib.get("target")
                if source and target:
                    left = labels.get(source, source)
                    right = labels.get(target, target)
                    edges.append(f"{left} -> {right}")
            node_labels = list(dict.fromkeys(labels.values()))
            sections = ["[Draw.io diagram nodes]", *node_labels]
            if edges:
                sections.extend(["[Draw.io diagram connections]", *edges])
            if not node_labels and not edges:
                raise ValueError(f"{filename}: no readable Draw.io nodes or connections were found.")
            return "\n".join(sections)

        sections: list[str] = []
        edges: list[str] = []
        for element in root.iter():
            tag = element.tag.rsplit("}", 1)[-1]
            attributes = element.attrib
            name = attributes.get("name") or attributes.get("label")
            identifier = attributes.get("id")
            if name:
                sections.append(f"{tag}: {name}")
            elif identifier and tag not in {"definitions", "process"}:
                sections.append(f"{tag}: {identifier}")
            if tag in {"sequenceFlow", "messageFlow", "association"}:
                source = attributes.get("sourceRef", "")
                target = attributes.get("targetRef", "")
                if source or target:
                    edges.append(f"{source} -> {target}")
            if element.text and element.text.strip() and len(element) == 0:
                sections.append(element.text.strip())
        if edges:
            sections.extend(["[Diagram connections]", *edges])
        if not sections:
            raise ValueError(f"{filename}: no readable diagram labels or XML elements were found.")
        return "\n".join(dict.fromkeys(sections))

    @staticmethod
    def _extract_docx(content: bytes) -> str:
        document = Document(io.BytesIO(content))
        sections = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
        for table_index, table in enumerate(document.tables, start=1):
            sections.append(f"[Table {table_index}]")
            for row in table.rows[:100]:
                sections.append(" | ".join(cell.text.strip() for cell in row.cells))
        return "\n".join(sections)

    def _extract_pptx(self, content: bytes, images: list[str]) -> str:
        presentation = Presentation(io.BytesIO(content))
        sections: list[str] = []
        for slide_index, slide in enumerate(presentation.slides, start=1):
            sections.append(f"[Slide {slide_index}]")
            for shape in slide.shapes:
                if getattr(shape, "has_text_frame", False) and shape.text.strip():
                    sections.append(shape.text.strip())
                if getattr(shape, "has_table", False):
                    for row in shape.table.rows[:50]:
                        sections.append(" | ".join(cell.text.strip() for cell in row.cells))
                if shape.shape_type == MSO_SHAPE_TYPE.PICTURE and len(images) < MAX_IMAGES:
                    try:
                        self._append_image(f"PowerPoint slide {slide_index}", shape.image.blob, images)
                    except (ValueError, OSError):
                        continue
        return "\n".join(sections)

    @staticmethod
    def _extract_xlsx(content: bytes) -> str:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sections: list[str] = []
        try:
            for worksheet in workbook.worksheets[:5]:
                sections.append(f"[Sheet: {worksheet.title}]")
                for row in worksheet.iter_rows(max_row=100, max_col=30, values_only=True):
                    values = ["" if value is None else str(value) for value in row]
                    if any(values):
                        sections.append(" | ".join(values))
        finally:
            workbook.close()
        return "\n".join(sections)

    @staticmethod
    def _append_image(filename: str, content: bytes, images: list[str]) -> None:
        if len(images) >= MAX_IMAGES:
            return
        try:
            with Image.open(io.BytesIO(content)) as source:
                if getattr(source, "width", 0) * getattr(source, "height", 0) > 40_000_000:
                    raise ValueError(f"{filename}: image dimensions exceed the 40-megapixel limit.")
                source.seek(0)
                image = ImageOps.exif_transpose(source)
                image.thumbnail((1800, 1800))
                if image.mode not in {"RGB", "L"}:
                    background = Image.new("RGB", image.size, "white")
                    if "A" in image.getbands():
                        background.paste(image, mask=image.getchannel("A"))
                    else:
                        background.paste(image.convert("RGB"))
                    image = background
                elif image.mode == "L":
                    image = image.convert("RGB")
                output = io.BytesIO()
                image.save(output, format="JPEG", quality=82, optimize=True)
        except (OSError, Image.DecompressionBombError) as error:
            raise ValueError(f"{filename}: image could not be decoded safely.") from error
        encoded = base64.b64encode(output.getvalue()).decode("ascii")
        images.append(f"data:image/jpeg;base64,{encoded}")
