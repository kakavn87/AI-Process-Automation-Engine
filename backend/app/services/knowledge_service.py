import hashlib
import logging
import math
import mimetypes
from pathlib import Path
from uuid import uuid4

from sqlalchemy import bindparam, func, text
from sqlalchemy.orm import Session
from pgvector.sqlalchemy import Vector

from app.core.config import settings
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.services.ai_service import AIService
from app.services.ai_usage_service import AIUsageService
from app.services.document_parser import extract_document, split_segments

logger = logging.getLogger(__name__)
MAX_DOCUMENT_BYTES = 25 * 1024 * 1024
EMBED_BATCH_SIZE = 48


class DocumentIngestionService:
    def __init__(self, db: Session, ai_service: AIService | None = None):
        self.db = db
        self.ai = ai_service or AIService()

    def ingest(self, filename: str, content: bytes, mime_type: str | None = None) -> dict:
        safe_name = Path(filename or "upload").name[:255]
        if len(content) > MAX_DOCUMENT_BYTES:
            raise ValueError("The document is larger than the 25 MB upload limit.")
        resolved_mime = mime_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
        suffix = Path(safe_name).suffix.lower()
        details = {}

        vision_text = None
        if suffix in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"} and self.ai.is_configured:
            try:
                vision_text = self.ai.describe_image(safe_name, content, resolved_mime)
                if vision_text:
                    details = {"visionUsed": True, "parser": "vision", "ocrUsed": False,
                               "segmentCount": 1, "characterCount": len(vision_text)}
                    if self.ai.last_call_telemetry:
                        AIUsageService(self.db).record(None, self.ai.last_call_telemetry)
            except Exception:
                logger.exception("Vision analysis failed; falling back to OCR.")
        if vision_text:
            segments = [{"text": vision_text, "locator": {"image": safe_name, "method": "vision"}}]
        else:
            segments, details = extract_document(safe_name, content, resolved_mime)

        chunks = split_segments(segments)
        if not chunks:
            raise ValueError("No indexable content was extracted from the file.")

        document_id = str(uuid4())
        document = KnowledgeDocument(
            id=document_id, workspace_id="default", file_name=safe_name,
            file_type=suffix.lstrip("."), mime_type=resolved_mime,
            checksum_sha256=hashlib.sha256(content).hexdigest(), byte_size=len(content),
            status="processing", extracted_text="\n\n".join(item["text"] for item in segments),
            source_metadata=details, raw_content=content,
        )
        self.db.add(document)
        self.db.flush()

        for start in range(0, len(chunks), EMBED_BATCH_SIZE):
            batch = chunks[start:start + EMBED_BATCH_SIZE]
            embeddings = []
            try:
                embeddings = self.ai.embed_texts([item["content"] for item in batch])
                if self.ai.last_call_telemetry:
                    AIUsageService(self.db).record(None, self.ai.last_call_telemetry)
            except Exception:
                logger.exception("Embedding generation failed; keyword retrieval will remain available.")
            for offset, item in enumerate(batch):
                embedding = embeddings[offset] if offset < len(embeddings) else None
                if embedding and len(embedding) != settings.EMBEDDING_DIMENSIONS:
                    logger.warning("Embedding dimension mismatch; storing this chunk without a vector.")
                    embedding = None
                self.db.add(KnowledgeChunk(
                    id=str(uuid4()), document_id=document_id, chunk_index=start + offset,
                    content=item["content"], source_locator=item["source_locator"], embedding=embedding,
                ))

        document.status = "ready"
        self.db.commit()
        self.db.refresh(document)
        return {
            "id": document.id, "fileName": document.file_name, "fileType": document.file_type,
            "mimeType": document.mime_type, "byteSize": document.byte_size,
            "status": document.status, "chunksCount": len(chunks),
            "sourceMetadata": document.source_metadata,
            "createdAt": document.created_at.isoformat() if document.created_at else None,
        }


class RAGService:
    def __init__(self, db: Session, ai_service: AIService | None = None):
        self.db = db
        self.ai = ai_service or AIService()

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0

    def search(self, query: str, document_ids: list[str], top_k: int = 8) -> list[dict]:
        ids = list(dict.fromkeys(document_ids))[:30]
        if not ids or not query.strip():
            return []
        query_embedding = []
        if self.ai.is_configured:
            try:
                vector = self.ai.embed_texts([query])
                query_embedding = vector[0] if vector else []
                if self.ai.last_call_telemetry:
                    AIUsageService(self.db).record(None, self.ai.last_call_telemetry)
            except Exception:
                logger.exception("RAG query embedding failed; using keyword retrieval.")

        if query_embedding and self.db.bind and self.db.bind.dialect.name == "postgresql":
            placeholders = []
            params = {"query_vector": query_embedding, "limit": max(1, min(top_k, 20))}
            for index, document_id in enumerate(ids):
                key = f"document_{index}"
                placeholders.append(f":{key}")
                params[key] = document_id
            statement = text(f"""
                SELECT c.id AS chunk_id, c.document_id, c.content, c.source_locator,
                       d.file_name, 1 - (c.embedding <=> :query_vector) AS score
                FROM knowledge_chunks c
                JOIN knowledge_documents d ON d.id = c.document_id
                WHERE d.status = 'ready' AND c.embedding IS NOT NULL
                  AND c.document_id IN ({", ".join(placeholders)})
                ORDER BY c.embedding <=> :query_vector
                LIMIT :limit
            """).bindparams(bindparam("query_vector", type_=Vector(settings.EMBEDDING_DIMENSIONS)))
            rows = self.db.execute(statement, params).mappings().all()
            if rows:
                return [{
                    "chunkId": row["chunk_id"], "documentId": row["document_id"],
                    "fileName": row["file_name"], "content": row["content"],
                    "sourceLocator": row["source_locator"] or {},
                    "score": round(float(row["score"]), 4) if row["score"] is not None else None,
                    "retrieval": "pgvector_cosine",
                } for row in rows]

        chunks = (
            self.db.query(KnowledgeChunk, KnowledgeDocument.file_name)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .filter(KnowledgeDocument.status == "ready", KnowledgeChunk.document_id.in_(ids))
            .limit(3000).all()
        )
        terms = {term.lower() for term in query.split() if len(term) > 2}
        ranked = []
        for chunk, file_name in chunks:
            if query_embedding and chunk.embedding:
                score, retrieval = self._cosine(query_embedding, chunk.embedding), "cosine_fallback"
            else:
                content_terms = {term.lower() for term in chunk.content.split() if len(term) > 2}
                score, retrieval = len(terms & content_terms) / max(1, len(terms)), "keyword_fallback"
            ranked.append((score, chunk, file_name, retrieval))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [{
            "chunkId": chunk.id, "documentId": chunk.document_id, "fileName": file_name,
            "content": chunk.content, "sourceLocator": chunk.source_locator or {},
            "score": round(float(score), 4), "retrieval": retrieval,
        } for score, chunk, file_name, retrieval in ranked[:max(1, min(top_k, 20))]]

    def build_context(self, query: str, document_ids: list[str], top_k: int = 8) -> dict:
        results = self.search(query, document_ids, top_k=top_k)
        excerpts, sources, seen = [], [], set()
        remaining = 12000
        for item in results:
            locator = item["sourceLocator"]
            label = ", ".join(f"{key}: {value}" for key, value in locator.items())
            citation = item["fileName"] + (f" ({label})" if label else "")
            content = item["content"][:remaining]
            if not content:
                break
            excerpts.append(f"[Source: {citation}]\n{content}")
            remaining -= len(content)
            source_key = (item["documentId"], citation)
            if source_key not in seen:
                sources.append({
                    "documentId": item["documentId"], "fileName": item["fileName"],
                    "locator": locator, "score": item["score"], "retrieval": item["retrieval"],
                })
                seen.add(source_key)
            if remaining <= 0:
                break
        return {"context": "\n\n".join(excerpts), "sources": sources, "retrievedChunks": len(excerpts)}

    def list_documents(self) -> list[dict]:
        rows = (
            self.db.query(KnowledgeDocument).filter(KnowledgeDocument.status == "ready")
            .order_by(KnowledgeDocument.created_at.desc()).limit(100).all()
        )
        counts = dict(
            self.db.query(KnowledgeChunk.document_id, func.count(KnowledgeChunk.id))
            .filter(KnowledgeChunk.document_id.in_([row.id for row in rows]))
            .group_by(KnowledgeChunk.document_id).all()
        ) if rows else {}
        return [{
            "id": row.id, "fileName": row.file_name, "fileType": row.file_type,
            "mimeType": row.mime_type, "byteSize": row.byte_size, "status": row.status,
            "chunksCount": int(counts.get(row.id, 0)),
            "createdAt": row.created_at.isoformat() if row.created_at else None,
        } for row in rows]
