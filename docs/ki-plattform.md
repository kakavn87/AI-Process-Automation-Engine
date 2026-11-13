# KI-Plattform: LiteLLM, Open WebUI und RAG

Diese Anleitung beschreibt die optionale KI-Plattform von FlowPilot. Die Prozessanalyse läuft weiterhin über das FastAPI-Backend. LiteLLM vermittelt die Modellaufrufe; Open WebUI ist ein zusätzlicher Chat-Arbeitsbereich. Qdrant speichert Vektoren für die prozessbezogene Dokumentensuche.

## Architektur

```text
Angular-Frontend
      |
      v
FastAPI-Backend ----------------------> PostgreSQL / SQLite
      |
      | OpenAI-kompatible API
      v
LiteLLM-Gateway ----------------------> OpenAI oder andere Modellanbieter
      ^
      |
Open WebUI (separater Chat-Zugang)

FastAPI-Backend ----------------------> Qdrant (RAG / Vektorsuche)
```

- **FastAPI** hält Anbieter-Schlüssel geheim und steuert Analyse, Dokumentenverarbeitung und Freigaben.
- **LiteLLM** bündelt Modellanbieter, Modell-Aliase und virtuelle API-Schlüssel. FlowPilot ruft LiteLLM über dessen OpenAI-kompatible API auf.
- **Open WebUI** ist eine eigenständige Chat-Oberfläche. Sie greift mit einem eigenen virtuellen Schlüssel auf LiteLLM zu. Sie ersetzt nicht das FlowPilot-Backend.
- **Qdrant** ist der Vektorspeicher für die optionale Suche in hochgeladenen Prozessdokumenten. Die Anwendung filtert Treffer nach Prozesssitzung.

## Lokaler Start mit Docker Compose

1. Wechseln Sie in den Ordner `infrastructure/docker`.
2. Kopieren Sie die Beispieldatei:

   ```bash
   cp .env.ai-platform.example .env.ai-platform
   ```

3. Tragen Sie in `.env.ai-platform` Ihren Provider-Schlüssel und ein langes, zufälliges LiteLLM-Administrationsgeheimnis ein. Die Platzhalter für `LITELLM_WEBUI_KEY` und `LITELLM_BACKEND_KEY` werden später durch getrennte virtuelle Schlüssel ersetzt.
4. Starten Sie zunächst Datenbank, Gateway und Vektorspeicher:

   ```bash
   docker compose --env-file .env.ai-platform --profile ai-platform up -d postgres litellm qdrant
   ```

5. Erstellen Sie in LiteLLM zwei getrennte virtuelle Schlüssel. Der Backend-Schlüssel darf nur die Modell-Aliase `process-analysis`, `process-vision` und `process-embeddings` verwenden. Der Open-WebUI-Schlüssel erhält nur die tatsächlich benötigten Chat-Modelle. Verwenden Sie dafür die LiteLLM-Verwaltung mit dem Master-Schlüssel.
6. Speichern Sie die erzeugten Schlüssel als `LITELLM_BACKEND_KEY` und `LITELLM_WEBUI_KEY` in `.env.ai-platform`. Starten Sie danach alle Dienste:

   ```bash
   docker compose --env-file .env.ai-platform --profile ai-platform up -d
   ```

Die Dienste sind in der Compose-Datei standardmäßig nur an `127.0.0.1` gebunden. Das ist für eine lokale Entwicklungsumgebung gedacht, nicht für einen öffentlich erreichbaren Produktivbetrieb.

## FastAPI-Backend konfigurieren

Wenn das Backend lokal auf demselben Rechner läuft, können Sie diese Werte in `backend/.env` eintragen:

```env
AI_GATEWAY_PROVIDER=litellm
OPENAI_BASE_URL=http://localhost:4000/v1
OPENAI_API_KEY=<LITELLM_BACKEND_KEY>
OPENAI_MODEL=process-analysis
OPENAI_VISION_MODEL=process-vision
RAG_EMBEDDING_MODEL=process-embeddings
OPENWEBUI_URL=http://localhost:3000
RAG_ENABLED=true
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=flowpilot_process_knowledge
RAG_VECTOR_SIZE=1536
```

Ersetzen Sie den Platzhalter durch den echten virtuellen Backend-Schlüssel. Starten Sie anschließend das Backend neu.

Wenn das Backend in einem eigenen Container läuft, ist `localhost` nicht der richtige Hostname für LiteLLM oder Qdrant. Verwenden Sie den jeweiligen Dienstnamen im gemeinsamen Docker-Netzwerk oder die interne Dienstadresse Ihres Hosting-Anbieters.

## Open WebUI konfigurieren

Der Compose-Dienst ist bereits mit folgenden internen Verbindungswerten vorbereitet:

- API-Adresse: `http://litellm:4000/v1`
- API-Schlüssel: `LITELLM_WEBUI_KEY`
- Anmeldung: aktiviert
- Datenhaltung: eigenes Docker-Volume

Die externe Adresse, unter der Benutzer Open WebUI erreichen, wird als `OPENWEBUI_URL` im FastAPI-Backend hinterlegt. Bei lokaler Entwicklung ist dies `http://localhost:3000`.

## Render und Produktivbetrieb

Die Render-Datei stellt aktuell das Angular-Frontend und das FastAPI-Backend bereit. Sie stellt **nicht automatisch** LiteLLM, Open WebUI oder Qdrant bereit. Diese Dienste benötigen eine eigene, vom Backend erreichbare Bereitstellung sowie eine passende Datenhaltung.

Für das Render-Backend sind – abhängig von der gewählten Infrastruktur – mindestens diese Werte erforderlich:

- `AI_GATEWAY_PROVIDER=litellm`
- `OPENAI_BASE_URL=https://<litellm-host>/v1`
- `OPENAI_API_KEY`: virtueller LiteLLM-Schlüssel nur für FlowPilot
- `OPENAI_MODEL=process-analysis`
- `OPENAI_VISION_MODEL=process-vision`
- `RAG_EMBEDDING_MODEL=process-embeddings`
- `OPENWEBUI_URL=https://<open-webui-host>`
- `QDRANT_URL` und bei Bedarf `QDRANT_API_KEY`

Aktivieren Sie `RAG_ENABLED=true` erst, wenn Qdrant erreichbar ist und das Einbettungsmodell die konfigurierte Vektorgröße liefert. Für `text-embedding-3-small` sind 1536 Dimensionen üblich; prüfen Sie bei einem anderen Modell die tatsächliche Ausgabedimension.

## Sicherheit und Kostenkontrolle

- Provider-Schlüssel gehören ausschließlich in die LiteLLM-Umgebung.
- Das FastAPI-Backend erhält einen eigenen virtuellen Schlüssel mit minimalen Modellrechten.
- Open WebUI erhält einen separaten virtuellen Schlüssel. Verwenden Sie nicht den Master-Schlüssel in einer Benutzeroberfläche.
- Niemals API-Schlüssel in Angular, im Browser-Speicher, in Git oder in öffentliche Protokolle schreiben.
- Die Statusanzeige in FlowPilot zeigt Konfigurationsinformationen, aber sie ersetzt keinen vollständigen Modell- oder Berechtigungstest.
- LiteLLM kann Ausgaben, virtuelle Schlüssel und Budgets verwalten. Die tatsächliche Abrechnung des Modellanbieters bleibt maßgeblich.
- RAG speichert Dokumentenvektoren. Aktivieren Sie es in einem Mehrbenutzerbetrieb erst mit Authentifizierung, Workspace-Isolation, Berechtigungen sowie Aufbewahrungs- und Löschregeln.

## Zuständigkeiten im Überblick

| Baustein | Aufgabe |
|---|---|
| Angular | Benutzeroberfläche, Upload und Freigaben |
| FastAPI | Prozesslogik, Dokumentenverarbeitung, sichere Modellaufrufe |
| LiteLLM | Modell-Routing, virtuelle Schlüssel und Nutzungssteuerung |
| Open WebUI | Zusätzliche Chat-Oberfläche |
| Qdrant | Vektorsuche in Prozessdokumenten |
| PostgreSQL | Anwendungs- und Gateway-Datenbank |
