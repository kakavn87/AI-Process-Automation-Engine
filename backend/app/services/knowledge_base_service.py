from __future__ import annotations

import re
from time import perf_counter
from uuid import NAMESPACE_URL, uuid5

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings


class KnowledgeBaseService:
    """Session-scoped vector knowledge store.

    Uploaded content is indexed only under a server-generated process session ID.
    RAG is opt-in and disabled by default. This does not replace authentication or
    tenant isolation; do not enable it on a public multi-user deployment.
    """

    def __init__(self) -> None:
        self.telemetry_events: list[dict] = []
        self.enabled = bool(settings.RAG_ENABLED)
        self.storage_configured = bool(settings.QDRANT_URL.strip())
        self.configured = bool(
            self.enabled
            and self.storage_configured
            and settings.OPENAI_API_KEY.strip()
        )
        self._qdrant: QdrantClient | None = None
        self._embedding_client: OpenAI | None = None

        # Keep Qdrant available for deletion even after RAG is switched off.
        if self.storage_configured:
            self._qdrant = QdrantClient(
                url=settings.QDRANT_URL.strip(),
                api_key=settings.QDRANT_API_KEY.strip() or None,
                timeout=8.0,
            )
        if self.configured:
            self._embedding_client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL.strip() or None,
                timeout=45.0,
                max_retries=1,
            )

    @staticmethod
    def _provider_name() -> str:
        provider = settings.AI_GATEWAY_PROVIDER.strip().lower()
        if provider == "litellm":
            return "litellm"
        if settings.OPENAI_BASE_URL.strip():
            return "openai_compatible"
        return "openai"

    def readiness(self) -> dict:
        if not settings.RAG_ENABLED:
            return {
                "enabled": False,
                "configured": False,
                "connected": False,
                "status": "disabled",
                "collection": settings.QDRANT_COLLECTION,
                "embeddingModel": settings.RAG_EMBEDDING_MODEL,
                "scope": "process_session",
                "message": "RAG is disabled. Enable it only after configuring an isolated knowledge store.",
            }

        if not settings.QDRANT_URL.strip() or not settings.OPENAI_API_KEY.strip():
            return {
                "enabled": True,
                "configured": False,
                "connected": False,
                "status": "setup_required",
                "collection": settings.QDRANT_COLLECTION,
                "embeddingModel": settings.RAG_EMBEDDING_MODEL,
                "scope": "process_session",
                "message": "Configure QDRANT_URL and a server-side embedding API key.",
            }

        try:
            client = self._qdrant or QdrantClient(
                url=settings.QDRANT_URL.strip(),
                api_key=settings.QDRANT_API_KEY.strip() or None,
                timeout=4.0,
            )
            client.get_collections()
            return {
                "enabled": True,
                "configured": True,
                "connected": True,
                "status": "ready",
                "collection": settings.QDRANT_COLLECTION,
                "embeddingModel": settings.RAG_EMBEDDING_MODEL,
                "scope": "process_session",
                "message": "Qdrant is reachable. Documents are isolated by process session ID.",
            }
        except Exception:
            return {
                "enabled": True,
                "configured": True,
                "connected": False,
                "status": "unavailable",
                "collection": settings.QDRANT_COLLECTION,
                "embeddingModel": settings.RAG_EMBEDDING_MODEL,
                "scope": "process_session",
                "message": "Qdrant is configured but could not be reached. Document analysis will use extracted text without vector retrieval.",
            }

    def _ensure_collection(self) -> None:
        if self._qdrant is None:
            raise RuntimeError("RAG is not configured.")
        collections = self._qdrant.get_collections().collections
        if any(item.name == settings.QDRANT_COLLECTION for item in collections):
            return
        self._qdrant.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=qmodels.VectorParams(
                size=settings.RAG_VECTOR_SIZE,
                distance=qmodels.Distance.COSINE,
            ),
        )

    @staticmethod
    def split_document_context(text: str) -> list[dict]:
        """Split extracted document text while preserving source filename and page."""
        source_sections: list[dict] = []
        current_source = "Uploaded documents"
        current_page: int | None = None
        current_lines: list[str] = []

        def flush() -> None:
            body = "\n".join(current_lines).strip()
            if body:
                source_sections.append({
                    "source_file": current_source,
                    "page": current_page,
                    "content": body,
                })
            current_lines.clear()

        for line in text.splitlines():
            source_match = re.match(r"^\[Source document: (.+)\]$", line.strip())
            page_match = re.match(r"^\[Page\s+(\d+)\]$", line.strip())
            if source_match:
                flush()
                current_source = source_match.group(1)[:200]
                current_page = None
            elif page_match:
                flush()
                current_page = int(page_match.group(1))
            else:
                current_lines.append(line)
        flush()

        chunks: list[dict] = []
        chunk_size = settings.RAG_CHUNK_CHARS
        overlap = min(settings.RAG_CHUNK_OVERLAP, chunk_size // 2)
        for section in source_sections:
            body = section["content"]
            start = 0
            while start < len(body):
                end = min(start + chunk_size, len(body))
                if end < len(body):
                    paragraph_end = body.rfind("\n", start + int(chunk_size * 0.65), end)
                    if paragraph_end > start:
                        end = paragraph_end
                content = body[start:end].strip()
                if content:
                    chunks.append({
                        "source_file": section["source_file"],
                        "page": section["page"],
                        "content": content,
                    })
                if end >= len(body):
                    break
                start = max(start + 1, end - overlap)
        return chunks

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if self._embedding_client is None:
            raise RuntimeError("RAG embedding client is not configured.")
        started = perf_counter()
        response = self._embedding_client.embeddings.create(
            model=settings.RAG_EMBEDDING_MODEL,
            input=texts,
        )
        vectors = [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
        usage = getattr(response, "usage", None)
        self.telemetry_events.append({
            "provider": self._provider_name(),
            "model": settings.RAG_EMBEDDING_MODEL,
            "task": "rag_embedding",
            "status": "success",
            "inputTokens": getattr(usage, "prompt_tokens", None) if usage else None,
            "outputTokens": 0,
            "totalTokens": getattr(usage, "total_tokens", None) if usage else None,
            "durationMs": round((perf_counter() - started) * 1000),
        })
        if len(vectors) != len(texts):
            raise RuntimeError("The embedding provider returned an incomplete vector batch.")
        if any(len(vector) != settings.RAG_VECTOR_SIZE for vector in vectors):
            raise RuntimeError(
                "Embedding dimensions do not match RAG_VECTOR_SIZE. "
                "Check the configured embedding model and vector size."
            )
        return vectors

    def index_session(self, session_id: str, extracted_text: str) -> dict:
        if not self.enabled:
            return {"enabled": False, "indexedChunks": 0, "status": "disabled"}
        if not self.configured:
            return {"enabled": True, "indexedChunks": 0, "status": "setup_required"}
        chunks = self.split_document_context(extracted_text)
        if not chunks:
            return {"enabled": True, "indexedChunks": 0, "status": "no_text"}
        if self._qdrant is None:
            raise RuntimeError("Qdrant client is not configured.")

        self._ensure_collection()
        vectors = self._embed([item["content"] for item in chunks])
        points = []
        for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
            stable_id = str(uuid5(
                NAMESPACE_URL,
                f"flowpilot:{session_id}:{index}:{chunk['source_file']}:{chunk['page']}:{chunk['content']}",
            ))
            points.append(qmodels.PointStruct(
                id=stable_id,
                vector=vector,
                payload={
                    "session_id": session_id,
                    "source_file": chunk["source_file"],
                    "page": chunk["page"],
                    "chunk_index": index,
                    "content": chunk["content"],
                },
            ))
        self._qdrant.upsert(
            collection_name=settings.QDRANT_COLLECTION,
            points=points,
            wait=True,
        )
        return {
            "enabled": True,
            "indexedChunks": len(points),
            "status": "indexed",
        }

    def delete_session(self, session_id: str) -> bool:
        """Delete every stored vector chunk belonging to one process session."""
        if self._qdrant is None:
            return False
        collections = self._qdrant.get_collections().collections
        if not any(item.name == settings.QDRANT_COLLECTION for item in collections):
            return True
        self._qdrant.delete(
            collection_name=settings.QDRANT_COLLECTION,
            points_selector=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="session_id",
                        match=qmodels.MatchValue(value=session_id),
                    )
                ]
            ),
            wait=True,
        )
        return True

    def search(self, session_id: str, query: str, top_k: int | None = None) -> list[dict]:
        if not self.enabled or not self.configured:
            raise RuntimeError("Session RAG is not enabled and configured.")
        if self._qdrant is None:
            raise RuntimeError("Qdrant client is not configured.")
        query = query.strip()
        if not query:
            return []
        self._ensure_collection()
        vector = self._embed([query])[0]
        response = self._qdrant.query_points(
            collection_name=settings.QDRANT_COLLECTION,
            query=vector,
            query_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="session_id",
                        match=qmodels.MatchValue(value=session_id),
                    )
                ]
            ),
            limit=min(max(top_k or settings.RAG_TOP_K, 1), 20),
            with_payload=True,
        )
        results = []
        for point in response.points:
            payload = point.payload or {}
            results.append({
                "sourceFile": payload.get("source_file", "Unknown source"),
                "page": payload.get("page"),
                "chunkIndex": payload.get("chunk_index"),
                "score": round(float(point.score), 4),
                "content": payload.get("content", ""),
            })
        return results
