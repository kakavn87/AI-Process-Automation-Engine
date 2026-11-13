# FlowPilot – Part 1 and Part 6

## Part 1 – Input, document ingestion and business knowledge

The process builder accepts a natural-language description and multiple business source files. The persistent knowledge parser supports PDF, DOCX, XLSX, PPTX, CSV, TXT, Markdown, PNG, JPG/JPEG, WEBP, TIFF, Draw.io XML, BPMN XML and generic XML.

### Ingestion pipeline

1. Validate file type, size and Office archive expansion limits. Uploaded content is untrusted input.
2. Extract native text and tables with format-specific parsers.
3. Preserve source locators including PDF page, Word paragraph/table row, PowerPoint slide/shape, Excel sheet/row and diagram name.
4. OCR scanned PDF pages and images with Tesseract. Raster diagrams/screenshots can use a configured vision-capable model first, with OCR fallback.
5. Parse BPMN and Draw.io XML labels and sequence references.
6. Normalize text, split it into bounded overlapping chunks, and retain the source locator for each chunk.
7. Generate embeddings in batches through the OpenAI-compatible AI endpoint. When using the local LiteLLM profile, the embedding alias is process-embeddings.
8. Persist document metadata, checksums, original file bytes, extracted text, chunks and optional embeddings. PostgreSQL uses pgvector; SQLite uses JSON-based fallback storage.
9. Retrieve only from document IDs explicitly selected for a process analysis. Include source filenames and locators in the AI context and response.

### Knowledge API

- POST /api/documents/upload: persist one source file (25 MB maximum).
- GET /api/documents: list indexed sources; when persistent knowledge is disabled, returns enabled=false and an empty list.
- POST /api/documents/search: retrieve chunks for selected document IDs.
- POST /api/processes/analyze-with-documents: analyze a description and newly uploaded files; the private persistence flag controls whether new uploads are retained for later use.
- POST /api/processes/analyze: optionally accepts document_ids to reuse previously indexed sources.

### RAG and evidence

RAG uses embedding vectors and pgvector cosine similarity on PostgreSQL. If embedding creation is unavailable, chunks remain searchable using keyword fallback. If vector search finds no matches, a local fallback ranking is used. Only a bounded set of excerpts is passed to the model. Retrieved content is explicitly identified as untrusted evidence, not instructions. The response includes knowledgeSources with document ID, source filename, page/slide/sheet/row/diagram locator, relevance score and retrieval mode.

### Privacy and deployment boundary

The public portfolio demo has no account authentication, tenant isolation or document-level ACL. Therefore KNOWLEDGE_PERSISTENCE_ENABLED defaults to false, as does PREVIEW_KNOWLEDGE_PERSISTENCE_ENABLED. In that mode, the existing one-request in-memory upload path remains in place and files are not added to a reusable shared knowledge base.

Enable persistent RAG only on a private instance after authentication, workspace/document authorization, retention and deletion controls, quotas and malware scanning are in place. This MVP stores source bytes in PostgreSQL; production should move originals to private S3-compatible object storage. Ingestion currently runs synchronously and should move to a worker queue before large-scale use.

## Part 6 – AI gateway, orchestration and controlled automation

### Responsibilities

- AIService: structured process analysis, image understanding and embedding creation.
- LiteLLM Proxy: shared OpenAI-compatible gateway; aliases are process-analysis, process-vision and process-embeddings.
- Open WebUI: optional internal prompt playground and knowledge assistant; it is not the source of truth for FlowPilot data or workflow logic.
- ProcessService: deterministic signals plus AI process specification, AS-IS process, opportunities, risks, assumptions, open questions and workflow proposal.
- WorkflowSessionService: durable clarification state and continuation after user answers.
- RAGService: selected-document retrieval and source citations.
- Approval/execution services: explicit human approval; simulation remains the default.

### AI request flow

1. Angular submits process text, new source files and selected saved-document IDs.
2. FastAPI validates file count and size.
3. On a private instance with persistent knowledge enabled, documents are extracted, OCR/vision processed, chunked and embedded. On the public demo, the existing in-memory upload path is used.
4. RAG retrieves relevant excerpts only from the selected document IDs and passes bounded evidence to ProcessService.
5. ProcessService combines the evidence with deterministic signals and calls the OpenAI Responses API through OPENAI_BASE_URL. LiteLLM is compatible through the same OpenAI-compatible gateway configuration.
6. AI returns structured AS-IS analysis, opportunities, risks, assumptions, questions and proposed workflow.
7. WorkflowSessionService persists the analysis and clarification state. Missing facts pause at needs_input; answers resume the existing session.
8. The user explicitly creates an approval request. Approval and execution are separate actions.
9. External actions remain simulated unless the separately configured HTTPS webhook is explicitly enabled and confirmed.

### LiteLLM model routing

Set OPENAI_BASE_URL to the LiteLLM /v1 endpoint, AI_GATEWAY_PROVIDER=litellm, and OPENAI_API_KEY to a least-privilege LiteLLM virtual key. Configure these model aliases:
- OPENAI_MODEL=process-analysis
- OPENAI_VISION_MODEL=process-vision
- OPENAI_EMBEDDING_MODEL=process-embeddings

The aliases can map to separate providers/models in infrastructure/docker/litellm-config.yaml without changing application code. The local Docker profile includes a dedicated PostgreSQL database for LiteLLM key and spend management. Keep the master key for gateway administration only. Generate separate scoped keys for FlowPilot and Open WebUI. The AI usage monitoring service records provider, model, task, token counts and duration when the upstream response includes usage metadata.

### Open WebUI integration

Open WebUI connects to LiteLLM through the OpenAI-compatible API. Use it as an internal AI workspace for prompt experiments, model comparison and employee-facing chat. Angular remains the customer-facing process product. Do not put privileged business logic in Open WebUI Functions or Pipes; restrict tools and administration.

### Safety rules

- Documents, filenames, diagrams and retrieved chunks are untrusted source data.
- Never invent approvers, recipients, channels, business rules, schedules, credentials or measured savings.
- Preserve source references and separate confirmed facts from assumptions.
- Outbound email, Teams, HTTP, financial or consequential actions require explicit human approval.
- Never expose the LiteLLM master key to a browser or production user.
- Public previews keep persistent knowledge disabled because the MVP has no authentication or tenant isolation.
- This implementation does not add native ERP, Outlook, Teams or Slack connectors.

## Local development – optional AI platform

1. Copy infrastructure/docker/.env.ai-platform.example to infrastructure/docker/.env.ai-platform.
2. Set a real provider API key and strong random LiteLLM master, salt and database secrets.
3. Start the profile from the repository root using the Docker Compose file in infrastructure/docker and the environment file just created.
4. Create separate LiteLLM virtual keys for the FlowPilot backend and Open WebUI. Do not use the master key for application traffic.
5. For a backend running on the host, configure OPENAI_BASE_URL=http://localhost:4000/v1, AI_GATEWAY_PROVIDER=litellm, OPENAI_MODEL=process-analysis, OPENAI_VISION_MODEL=process-vision, OPENAI_EMBEDDING_MODEL=process-embeddings, and OPENWEBUI_URL=http://localhost:3000.
6. Set DATABASE_URL to postgresql+psycopg://app:YOUR_APP_DB_PASSWORD@localhost:5432/process_automation and APP_DB_PASSWORD to the same local secret used by Compose. Enable KNOWLEDGE_PERSISTENCE_ENABLED=true only on a private, authenticated instance with pgvector available.

Local endpoints: Open WebUI at localhost:3000, LiteLLM at localhost:4000, PostgreSQL at localhost:5432, and FlowPilot API documentation at localhost:8000/docs.

## Known MVP limitations

- Persistent knowledge has no user/tenant ACL yet; it must stay off on public deployments.
- Source file bytes are in PostgreSQL; production object storage is still required.
- Ingestion and embedding run synchronously in the API request.
- Malware scanning, quotas, deletion UI, migrations and enterprise retention controls are not implemented.
- Vision and embeddings require configured compatible model aliases; OCR/keyword fallback is available where implemented.
- Native third-party business connectors are not part of this change.


### Default model selection (November 2026)

The included LiteLLM example maps `process-analysis` to `gpt-6-luna` for cost-efficient high-volume structured analysis, and `process-vision` to `gpt-6.1-terra` for visual reasoning over process diagrams and screenshots. `process-embeddings` uses `text-embedding-3-small`; its output dimensions must match `EMBEDDING_DIMENSIONS=1536`. These are example defaults and can be changed by editing the LiteLLM model map. GPT-4o mini is intentionally not used in the new configuration because the API deprecation notice lists January 14, 2027 as its shutdown date.
