from __future__ import annotations

from typing import Any


TEXT_DE = {
    "Collect inputs": "Eingaben erfassen",
    "Extract data": "Daten extrahieren",
    "Transform and consolidate data": "Daten umwandeln und zusammenführen",
    "Validate data": "Daten validieren",
    "Calculate results": "Ergebnisse berechnen",
    "Generate output": "Ausgabe erstellen",
    "Obtain human approval": "Menschliche Freigabe einholen",
    "Notify recipients": "Empfänger benachrichtigen",
    "Update system records": "Systemdaten aktualisieren",
    "Finance team": "Finanzteam",
    "Employee": "Mitarbeitende",
    "Manager": "Führungskraft",
    "Customer": "Kunde",
    "Receive process inputs and attachments through email.": "Prozesseingaben und Anhänge per E-Mail empfangen.",
    "Download and inspect PDF and spreadsheet attachments.": "PDF- und Tabellenanhänge herunterladen und prüfen.",
    "Extract relevant values from the source documents.": "Relevante Werte aus den Quelldokumenten extrahieren.",
    "Combine extracted values in a master spreadsheet.": "Extrahierte Werte in einer zentralen Tabelle zusammenführen.",
    "Check data completeness and identify missing or inconsistent values.": "Daten auf Vollständigkeit prüfen und fehlende oder widersprüchliche Werte erkennen.",
    "Calculate the required results and prepare the output.": "Erforderliche Ergebnisse berechnen und die Ausgabe vorbereiten.",
    "Create a summary report for the intended audience.": "Einen zusammenfassenden Bericht für die Zielgruppe erstellen.",
    "Ask a manager to review and approve the report.": "Den Bericht von einer Führungskraft prüfen und freigeben lassen.",
    "Share the approved report with the team in Microsoft Teams.": "Den freigegebenen Bericht mit dem Team in Microsoft Teams teilen.",
    "Distribute the completed output to the relevant recipients.": "Die fertige Ausgabe an die zuständigen Empfänger verteilen.",
    "Collect email attachments": "E-Mail-Anhänge erfassen",
    "Monitor a designated mailbox and collect matching attachments automatically.": "Ein festgelegtes Postfach überwachen und passende Anhänge automatisch erfassen.",
    "Extract document data": "Dokumentdaten extrahieren",
    "Read supported PDF and spreadsheet files and map values to a common data structure.": "Unterstützte PDF- und Tabellendateien auslesen und Werte in eine einheitliche Datenstruktur überführen.",
    "Consolidate spreadsheet data": "Tabellendaten zusammenführen",
    "Combine records into a standardized dataset instead of copying values manually.": "Datensätze zu einem standardisierten Datenbestand zusammenführen, statt Werte manuell zu kopieren.",
    "Validate data quality": "Datenqualität prüfen",
    "Check required fields, duplicates, and invalid values; route exceptions for correction.": "Pflichtfelder, Duplikate und ungültige Werte prüfen und Ausnahmen zur Korrektur weiterleiten.",
    "Generate recurring reports": "Wiederkehrende Berichte erstellen",
    "Calculate agreed metrics and create a consistent report from validated data.": "Vereinbarte Kennzahlen berechnen und aus validierten Daten einen einheitlichen Bericht erstellen.",
    "Notify through Microsoft Teams": "Über Microsoft Teams benachrichtigen",
    "Send the report link and a concise summary only after approval.": "Den Berichtslink und eine kurze Zusammenfassung erst nach der Freigabe versenden.",
    "Map repetitive work": "Wiederkehrende Arbeitsschritte erfassen",
    "Identify repeated manual steps, decision points, and system handoffs before selecting automations.": "Wiederkehrende manuelle Schritte, Entscheidungspunkte und Systemübergaben vor der Automatisierung identifizieren.",
    "Scheduler": "Zeitplaner",
    "Start the workflow on the agreed weekly schedule.": "Den Workflow zum vereinbarten wöchentlichen Zeitpunkt starten.",
    "Find incoming messages and download matching attachments.": "Eingehende Nachrichten finden und passende Anhänge herunterladen.",
    "PDF parser": "PDF-Parser",
    "Extract text and tabular values from PDF files.": "Text und Tabellenwerte aus PDF-Dateien extrahieren.",
    "Excel / Spreadsheet processor": "Excel- und Tabellenverarbeitung",
    "Read, normalize, validate, and consolidate spreadsheet rows.": "Tabellenzeilen einlesen, normalisieren, validieren und zusammenführen.",
    "Deliver the approved report to the selected channel.": "Den freigegebenen Bericht an den ausgewählten Kanal übermitteln.",
    "A human review gate is recommended before the report is distributed.": "Vor der Verteilung des Berichts wird eine menschliche Prüfung empfohlen.",
    "No external distribution step was detected; add an approval gate for consequential actions.": "Es wurde keine externe Verteilung erkannt. Für folgenreiche Aktionen sollte eine Freigabe ergänzt werden.",
    "Final report distribution": "Verteilung des Abschlussberichts",
    "Not detected": "Nicht erkannt",
    "Validate extracted values against the source files before using them in calculations.": "Extrahierte Werte vor der Verwendung in Berechnungen mit den Quelldateien abgleichen.",
    "Define an explicit exception path for missing, unreadable, or duplicate attachments.": "Einen klaren Ausnahmeprozess für fehlende, unlesbare oder doppelte Anhänge festlegen.",
    "Restrict access to financial data and keep an auditable record of changes and approvals.": "Den Zugriff auf Finanzdaten beschränken und Änderungen sowie Freigaben revisionssicher dokumentieren.",
    "Do not send the final report until the designated manager has approved it.": "Den Abschlussbericht erst versenden, wenn die zuständige Führungskraft ihn freigegeben hat.",
    "Source files have reasonably consistent layouts that can be parsed reliably.": "Die Quelldateien haben ausreichend einheitliche Strukturen und können zuverlässig ausgelesen werden.",
    "A named manager or authorized role is available to review the generated output.": "Eine benannte Führungskraft oder berechtigte Rolle steht für die Prüfung der erstellten Ausgabe zur Verfügung.",
    "Which exact mailbox, folder, or source location should the process monitor?": "Welches konkrete Postfach, welchen Ordner oder Speicherort soll der Prozess überwachen?",
    "Where does the process receive its input data?": "Woher bezieht der Prozess seine Eingabedaten?",
    "Which fields and validation rules are mandatory, and what should happen when data is missing?": "Welche Felder und Prüfregeln sind verpflichtend, und was soll bei fehlenden Daten passieren?",
    "Who is the authorized approver, and where should the approval request appear?": "Wer ist freigabeberechtigt, und wo soll die Freigabeanfrage erscheinen?",
    "Which Microsoft Teams channel should receive the approved report?": "Welcher Microsoft-Teams-Kanal soll den freigegebenen Bericht erhalten?",
    "Analyzed with deterministic Python rules. Process details are inferred from detected phrases; external systems are not connected and workflow execution remains simulated.": "Mit deterministischen Python-Regeln analysiert. Prozessdetails werden aus erkannten Formulierungen abgeleitet; externe Systeme sind nicht verbunden und die Workflow-Ausführung wird nur simuliert.",
    "The description contains a process that should be mapped into clear steps before automation is designed.": "Die Beschreibung enthält einen Prozess, der vor der Automatisierung zunächst in klare Schritte gegliedert werden sollte.",
    "a recurring weekly trigger": "einen wiederkehrenden wöchentlichen Auslöser",
    "email-based input collection": "Eingangserfassung per E-Mail",
    "document and spreadsheet data extraction": "Datenextraktion aus Dokumenten und Tabellen",
    "report generation": "Berichterstellung",
    "a human approval gate before distribution": "eine menschliche Freigabe vor der Verteilung",
    "Microsoft Teams delivery": "Bereitstellung über Microsoft Teams",
    "Python rules were selected manually. This path does not call an LLM.": "Python-Regeln wurden manuell ausgewählt. Dieser Weg ruft kein LLM auf.",
    "AI analysis was selected manually; the backend will call the configured LLM.": "Die KI-Analyse wurde manuell ausgewählt. Das Backend ruft das konfigurierte LLM auf.",
    "AI analysis was requested, but OPENAI_API_KEY is not configured. Python rules were used instead.": "Die KI-Analyse wurde angefordert, aber OPENAI_API_KEY ist nicht konfiguriert. Stattdessen wurden Python-Regeln verwendet.",
    "The process matches supported activities and has enough context for deterministic analysis. Python rules were selected to avoid an unnecessary LLM call.": "Der Prozess passt zu unterstützten Aktivitäten und enthält genügend Kontext für eine regelbasierte Analyse. Python-Regeln wurden gewählt, um einen unnötigen LLM-Aufruf zu vermeiden.",
    "The process is ambiguous or outside the current rules coverage. The configured LLM was selected for semantic analysis.": "Der Prozess ist mehrdeutig oder wird von den aktuellen Regeln nicht ausreichend abgedeckt. Für die semantische Analyse wurde das konfigurierte LLM gewählt.",
    "The process is outside the current rules coverage, but no LLM API key is configured. The deterministic fallback will provide a best-effort proposal.": "Der Prozess liegt außerhalb der aktuellen Regelabdeckung, aber es ist kein LLM-API-Schlüssel konfiguriert. Die deterministische Fallback-Analyse erstellt einen bestmöglichen Vorschlag.",
    "The LLM request failed. The deterministic Python fallback was used instead; check API billing, model access, and backend logs.": "Die LLM-Anfrage ist fehlgeschlagen. Stattdessen wurde der deterministische Python-Fallback verwendet. Bitte API-Abrechnung, Modellzugriff und Backend-Protokolle prüfen.",
    "The OpenAI request could not be completed. A deterministic rules-based fallback was used.": "Die OpenAI-Anfrage konnte nicht abgeschlossen werden. Stattdessen wurde eine deterministische regelbasierte Analyse verwendet.",
    "Start workflow": "Workflow starten",
    "Human approval": "Menschliche Freigabe",
    "Pause until an authorized person reviews and approves the output.": "Anhalten, bis eine berechtigte Person die Ausgabe geprüft und freigegeben hat.",
    "Prepare process output": "Prozessausgabe vorbereiten",
    "Prepare the output defined by the process owner.": "Die von der Prozessverantwortung definierte Ausgabe vorbereiten.",
    "Generate report": "Bericht erstellen",
    "Create the report or document from validated data and agreed business rules.": "Den Bericht oder das Dokument anhand validierter Daten und vereinbarter Geschäftsregeln erstellen.",
    "Generate invoice": "Rechnung erstellen",
    "Normalize and consolidate data": "Daten normalisieren und zusammenführen",
    "Standardize field names and values, then combine records into a consistent dataset.": "Feldnamen und Werte standardisieren und Datensätze in einem einheitlichen Datenbestand zusammenführen.",
    "Validate source data": "Quelldaten validieren",
    "Check required fields, duplicates, invalid values, and unresolved exceptions.": "Pflichtfelder, Duplikate, ungültige Werte und offene Ausnahmen prüfen.",
    "Calculate process results": "Prozessergebnisse berechnen",
    "Apply the agreed calculations to validated records.": "Die vereinbarten Berechnungen auf validierte Datensätze anwenden.",
    "Collect email attachments": "E-Mail-Anhänge erfassen",
    "Find matching messages and download supported attachments.": "Passende Nachrichten finden und unterstützte Anhänge herunterladen.",
    "Generate report": "Bericht erstellen",
    "Create the report or document from validated data and agreed business rules.": "Den Bericht oder das Dokument anhand validierter Daten und vereinbarter Geschäftsregeln erstellen.",
    "Generate invoice": "Rechnung erstellen",
    "Prepare the invoice output from validated source data.": "Die Rechnungsausgabe anhand validierter Quelldaten vorbereiten.",
    "Notify through Microsoft Teams": "Über Microsoft Teams benachrichtigen",
    "Notify through Slack": "Über Slack benachrichtigen",
    "Publish the approved report or result to the configured Teams channel after approval.": "Den freigegebenen Bericht oder das Ergebnis nach der Freigabe im konfigurierten Teams-Kanal veröffentlichen.",
    "Post the approved result to the configured Slack destination after approval.": "Das freigegebene Ergebnis nach der Freigabe im konfigurierten Slack-Ziel veröffentlichen.",
    "Deliver the approved result through the configured {channel} destination after approval.": "Das freigegebene Ergebnis nach der Freigabe über den konfigurierten Kanal {channel} übermitteln.",
    "Prepare the invoice output from validated source data.": "Die Rechnungsausgabe anhand validierter Quelldaten vorbereiten.",
    "Prepare process output": "Prozessausgabe vorbereiten",
    "Pause until an authorized person reviews and approves the prepared output.": "Anhalten, bis eine berechtigte Person die vorbereitete Ausgabe geprüft und freigegeben hat.",
    "Notify Microsoft Teams": "Microsoft Teams benachrichtigen",
    "Publish the approved report or result to the configured Teams channel after approval.": "Den freigegebenen Bericht oder das Ergebnis nach der Freigabe im konfigurierten Teams-Kanal veröffentlichen.",
    "Send approved email": "Freigegebene E-Mail versenden",
    "Send the prepared output to the configured recipients after approval.": "Die vorbereitete Ausgabe nach der Freigabe an die konfigurierten Empfänger versenden.",
    "Notify Slack": "Slack benachrichtigen",
    "Post the approved result to the configured Slack destination after approval.": "Das freigegebene Ergebnis nach der Freigabe im konfigurierten Slack-Ziel veröffentlichen.",
    "Notify configured recipients": "Konfigurierte Empfänger benachrichtigen",
    "Deliver the result through a destination that must be selected by the process owner.": "Das Ergebnis über einen von der Prozessverantwortung auszuwählenden Kanal übermitteln.",
}

DOMAIN_DE = {
    "finance": "Finanzen", "human_resources": "Personalwesen", "sales": "Vertrieb",
    "procurement": "Einkauf", "customer_support": "Kundenservice", "operations": "Betrieb & Verwaltung",
    "logistics": "Logistik", "manufacturing": "Produktion", "it_operations": "IT-Betrieb",
    "marketing": "Marketing", "legal_compliance": "Recht & Compliance",
    "project_management": "Projektmanagement",
}

DAY_DE = {
    "Monday": "Montag", "Tuesday": "Dienstag", "Wednesday": "Mittwoch",
    "Thursday": "Donnerstag", "Friday": "Freitag", "Saturday": "Samstag", "Sunday": "Sonntag",
}


def translate_text(value: str, language: str = "de") -> str:
    if language != "de":
        return value
    if value in TEXT_DE:
        return TEXT_DE[value]
    if value.startswith("The process includes ") and value.endswith("."):
        parts = value[len("The process includes "):-1].split(", ")
        translated = [TEXT_DE.get(part, part) for part in parts]
        return "Der Prozess umfasst " + ", ".join(translated) + "."
    if value.startswith("Collect inputs from "):
        return "Eingaben aus " + value[len("Collect inputs from "):] + " erfassen"
    if value.startswith("Notify through "):
        return "Über " + value[len("Notify through "):] + " benachrichtigen"
    if value.startswith("Deliver the approved result through the configured ") and value.endswith(" destination after approval."):
        channel = value[len("Deliver the approved result through the configured "):-len(" destination after approval.")]
        return f"Das freigegebene Ergebnis nach der Freigabe über {channel} übermitteln."
    if value.startswith("Read supported ") and " files and map the required fields" in value:
        formats = value[len("Read supported "):].split(" files and map the required fields", 1)[0]
        return f"Unterstützte {formats}-Dateien auslesen und die erforderlichen Felder strukturierten Datensätzen zuordnen."
    if value.startswith("Retrieve new process inputs from the configured "):
        source = value[len("Retrieve new process inputs from the configured "):-len(" source.")]
        return f"Neue Prozesseingaben aus der konfigurierten Quelle {source} abrufen."
    if value.startswith("Weekly ") and value.endswith(" Reporting"):
        area = value[len("Weekly "):-len(" Reporting")]
        area_de = {"Finance": "Finanz", "HR": "Personal", "Sales": "Vertriebs", "Procurement": "Einkaufs", "Customer Support": "Kundenservice", "Logistics": "Logistik", "Manufacturing": "Produktions", "IT Operations": "IT-Betriebs", "Marketing": "Marketing", "Legal & Compliance": "Compliance", "Project Management": "Projekt", "Facilities": "Facility"}.get(area, area)
        return f"Wöchentlicher {area_de}bericht"
    if value.endswith(" Process Workflow"):
        area = value[:-len(" Process Workflow")]
        area_de = {"Finance": "Finanz", "HR": "Personal", "Sales": "Vertriebs", "Procurement": "Einkaufs", "Customer Support": "Kundenservice", "Logistics": "Logistik", "Manufacturing": "Produktions", "IT Operations": "IT-Betriebs", "Marketing": "Marketing", "Legal & Compliance": "Compliance", "Project Management": "Projekt", "Facilities": "Facility"}.get(area, area)
        return f"{area_de}-Workflow"
    if value == "Proposed Process Workflow":
        return "Vorgeschlagener Prozess-Workflow"
    if value.startswith("Extract supported ") and value.endswith(" files."):
        return "Unterstützte " + value[len("Extract supported "):-len(" files.")] + "-Dateien auslesen."
    if value.startswith("Run every week"):
        day_part = value.removeprefix("Run every week").removesuffix(" at the agreed time.")
        day_part = day_part.replace(" on ", " am ")
        for day, german_day in DAY_DE.items():
            day_part = day_part.replace(day, german_day)
        return "Wöchentlich" + day_part + " zum vereinbarten Zeitpunkt ausführen."
    if value == "Run every day at the agreed time.":
        return "Täglich zum vereinbarten Zeitpunkt ausführen."
    if value == "Run every month at the agreed time.":
        return "Monatlich zum vereinbarten Zeitpunkt ausführen."
    if value == "Run when new matching input arrives in the configured source.":
        return "Starten, sobald passende neue Eingaben in der konfigurierten Quelle eintreffen."
    if value == "Start manually until a trigger is configured.":
        return "Bis zur Konfiguration eines Auslösers manuell starten."
    if value.startswith("Analyzed with OpenAI Responses API ("):
        model = value.split("(", 1)[1].split(")", 1)[0]
        return f"Mit der OpenAI Responses API ({model}) analysiert. Integrationen sind nicht verbunden; die Workflow-Ausführung wird nur simuliert."
    return value


def localize_tree(value: Any, language: str = "de") -> Any:
    if language != "de":
        return value
    if isinstance(value, str):
        return translate_text(value, language)
    if isinstance(value, list):
        return [localize_tree(item, language) for item in value]
    if isinstance(value, dict):
        localized = {key: localize_tree(item, language) for key, item in value.items()}
        if localized.get("businessDomain") in DOMAIN_DE:
            localized["businessDomainLabel"] = DOMAIN_DE[localized["businessDomain"]]
        if localized.get("cadence", {}).get("day") in DAY_DE:
            localized["cadence"]["day"] = DAY_DE[localized["cadence"]["day"]]
        return localized
    return value


def localize_process_analysis(analysis: dict, language: str = "de") -> dict:
    if language != "de":
        return analysis
    result = localize_tree(analysis, language)
    if isinstance(result.get("detectedDetails"), dict):
        domain = result["detectedDetails"].get("businessDomain")
        if domain in DOMAIN_DE:
            result["detectedDetails"]["businessDomainLabel"] = DOMAIN_DE[domain]
    return result


def localize_workflow(workflow: dict, language: str = "de") -> dict:
    if language != "de":
        return workflow
    return localize_tree(workflow, language)


def localize_upload_result(result: dict, language: str = "de") -> dict:
    if language != "de":
        return result
    localized = dict(result)
    localized["processingSteps"] = [
        "Hochgeladene Datei im Arbeitsspeicher einlesen.",
        "Leere Zellen und Spaltennamen normalisieren.",
        "Spaltentypen und fehlende Werte erkennen.",
        f"{result.get('duplicateRows', 0)} doppelte Zeile(n) in der Vorschau erkannt und entfernt.",
        "Vorschau mit bis zu 10 bereinigten Zeilen erstellen.",
    ]
    localized["notice"] = (
        "Es wurden nur die ersten 20.000 nicht leeren Datenzeilen verarbeitet."
        if result.get("truncated")
        else "Die Datei wurde nur im Arbeitsspeicher verarbeitet und nicht gespeichert."
    )
    for column in localized.get("columns", []):
        types = {"number": "Zahl", "text": "Text", "boolean": "Boolesch", "mixed": "Gemischt", "empty": "Leer"}
        column["detectedType"] = types.get(column.get("detectedType"), column.get("detectedType"))
    return localized
