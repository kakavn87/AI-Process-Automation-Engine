import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';
import { ApprovalExecution, TabularDataResult } from '../../../../core/models/api.models';
import { ProcessStore } from '../../process.store';
import { ProcessService } from '../../process.service';

type AppLanguage = 'de' | 'en';
type AnalysisStrategy = 'auto' | 'rules' | 'llm';

interface Industry {
  id: string;
  icon: string;
  nameDe: string;
  nameEn: string;
  descriptionDe: string;
  descriptionEn: string;
  sampleDe: string;
  sampleEn: string;
}

@Component({
  selector: 'app-process-page',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './process-page.component.html'
})
export class ProcessPageComponent {
  readonly store = inject(ProcessStore);
  private readonly service = inject(ProcessService);
  private readonly api = inject(ApiService);

  readonly language = signal<AppLanguage>('de');
  readonly selectedDomain = signal('general');
  readonly execution = signal<ApprovalExecution | null>(null);
  readonly executionLoading = signal(false);
  readonly executionError = signal<string | null>(null);
  readonly dataResult = signal<TabularDataResult | null>(null);
  readonly dataProcessing = signal(false);
  readonly dataError = signal<string | null>(null);

  selectedDataFile: File | null = null;
  description = '';
  analysisStrategy: AnalysisStrategy = 'auto';

  readonly industries: Industry[] = [
    {
      id: 'finance', icon: '€',
      nameDe: 'Finanzen & Controlling', nameEn: 'Finance & Controlling',
      descriptionDe: 'Rechnungen, Zahlungen, Monatsabschlüsse und Reports',
      descriptionEn: 'Invoices, payments, month-end close and reporting',
      sampleDe: 'Jeden Monat erhält die Finanzabteilung Eingangsrechnungen als PDF per E-Mail. Die Rechnungsdaten werden manuell geprüft, mit Bestellungen abgeglichen, in SAP übertragen und zur Zahlung freigegeben.',
      sampleEn: 'Every month, Finance receives supplier invoices as PDF attachments. Invoice data is checked, matched with purchase orders, entered into SAP and submitted for payment approval.'
    },
    {
      id: 'human_resources', icon: '♙',
      nameDe: 'Personalwesen', nameEn: 'Human Resources',
      descriptionDe: 'Onboarding, Urlaubsanträge, Personalakten und Payroll',
      descriptionEn: 'Onboarding, leave requests, employee records and payroll',
      sampleDe: 'Bei jeder Neueinstellung sammelt HR die Vertrags- und Stammdaten, fordert fehlende Unterlagen an, erstellt eine Onboarding-Checkliste und informiert IT sowie die Führungskraft.',
      sampleEn: 'For every new hire, HR collects contract and employee data, requests missing documents, creates an onboarding checklist and notifies IT and the hiring manager.'
    },
    {
      id: 'sales', icon: '↗',
      nameDe: 'Vertrieb & CRM', nameEn: 'Sales & CRM',
      descriptionDe: 'Leads, Angebote, Pipeline und Kundenpflege',
      descriptionEn: 'Leads, quotations, pipeline and customer management',
      sampleDe: 'Neue Leads aus dem Webformular werden täglich geprüft, nach Branche und Potenzial kategorisiert, dem passenden Vertriebsmitarbeiter zugewiesen und als Aktivität im CRM dokumentiert.',
      sampleEn: 'New web-form leads are reviewed daily, categorized by industry and potential, assigned to the right sales representative and logged as CRM activities.'
    },
    {
      id: 'procurement', icon: '▤',
      nameDe: 'Einkauf & Beschaffung', nameEn: 'Procurement',
      descriptionDe: 'Bestellungen, Lieferanten, Angebote und Freigaben',
      descriptionEn: 'Purchase orders, suppliers, quotations and approvals',
      sampleDe: 'Wöchentlich werden offene Bestellungen und Liefertermine aus SAP ausgewertet. Verspätete Lieferungen werden markiert, Lieferanten kontaktiert und kritische Abweichungen an den Einkauf gemeldet.',
      sampleEn: 'Open purchase orders and delivery dates are reviewed weekly in SAP. Delayed deliveries are flagged, suppliers are contacted and critical exceptions are escalated to Procurement.'
    },
    {
      id: 'customer_support', icon: '◎',
      nameDe: 'Kundenservice', nameEn: 'Customer Service',
      descriptionDe: 'Tickets, Beschwerden, SLA und Wissensdatenbank',
      descriptionEn: 'Tickets, complaints, SLAs and knowledge base',
      sampleDe: 'Eingehende Kundenanfragen werden aus dem Postfach erfasst, nach Thema und Dringlichkeit klassifiziert, dem zuständigen Team zugeordnet und anhand der SLA-Frist priorisiert.',
      sampleEn: 'Incoming customer requests are captured from the shared inbox, classified by topic and urgency, routed to the right team and prioritized by SLA deadlines.'
    },
    {
      id: 'logistics', icon: '⇄',
      nameDe: 'Logistik & Lager', nameEn: 'Logistics & Warehouse',
      descriptionDe: 'Bestände, Wareneingang, Versand und Lieferstatus',
      descriptionEn: 'Inventory, goods receipt, shipping and delivery status',
      sampleDe: 'Jeden Morgen werden Lagerbestände und offene Lieferungen abgeglichen. Unterschreitungen des Mindestbestands werden erkannt, Nachbestellvorschläge erstellt und an die Disposition zur Prüfung gegeben.',
      sampleEn: 'Every morning, inventory levels are reconciled with open deliveries. Items below minimum stock are identified, replenishment proposals are created and sent to planners for review.'
    },
    {
      id: 'manufacturing', icon: '⚙',
      nameDe: 'Produktion & Qualität', nameEn: 'Manufacturing & Quality',
      descriptionDe: 'Produktionsplanung, Prüfprotokolle und Abweichungen',
      descriptionEn: 'Production planning, inspection records and deviations',
      sampleDe: 'Nach jeder Schicht werden Produktionsmengen und Qualitätsprüfungen erfasst. Abweichungen von Toleranzwerten werden erkannt, dokumentiert und an die Qualitätsleitung eskaliert.',
      sampleEn: 'After each shift, production volumes and quality inspections are recorded. Deviations from tolerance limits are detected, documented and escalated to Quality Management.'
    },
    {
      id: 'it_operations', icon: '⌘',
      nameDe: 'IT & Helpdesk', nameEn: 'IT & Helpdesk',
      descriptionDe: 'IT-Tickets, Zugriffsrechte, Incidents und Changes',
      descriptionEn: 'IT tickets, access rights, incidents and changes',
      sampleDe: 'Neue IT-Tickets werden automatisch nach Kategorie, Auswirkung und Dringlichkeit sortiert. Standardanfragen erhalten eine passende Checkliste, kritische Incidents werden an den Bereitschaftsdienst eskaliert.',
      sampleEn: 'New IT tickets are classified by category, impact and urgency. Standard requests receive the right checklist, while critical incidents are escalated to the on-call team.'
    },
    {
      id: 'marketing', icon: '◈',
      nameDe: 'Marketing & Kommunikation', nameEn: 'Marketing & Communications',
      descriptionDe: 'Kampagnen, Content-Freigaben und Performance-Reports',
      descriptionEn: 'Campaigns, content approvals and performance reports',
      sampleDe: 'Jeden Montag werden Kampagnendaten aus den Werbeplattformen gesammelt, nach Kanal konsolidiert, KPIs wie CPC und Conversion Rate berechnet und als Wochenreport für das Marketingteam aufbereitet.',
      sampleEn: 'Every Monday, campaign data is collected from advertising platforms, consolidated by channel, KPIs such as CPC and conversion rate are calculated and a weekly report is prepared for Marketing.'
    },
    {
      id: 'legal_compliance', icon: '§',
      nameDe: 'Recht & Compliance', nameEn: 'Legal & Compliance',
      descriptionDe: 'Vertragsprüfung, Richtlinien, Fristen und Nachweise',
      descriptionEn: 'Contract review, policies, deadlines and audit evidence',
      sampleDe: 'Eingehende Verträge werden zentral registriert, nach Vertragstyp und Ablaufdatum klassifiziert und auf fehlende Pflichtangaben geprüft. Kritische Klauseln werden zur juristischen Prüfung markiert.',
      sampleEn: 'Incoming contracts are registered centrally, classified by contract type and expiry date, and checked for missing mandatory information. Critical clauses are flagged for legal review.'
    },
    {
      id: 'project_management', icon: '▦',
      nameDe: 'Projektmanagement', nameEn: 'Project Management',
      descriptionDe: 'Statusberichte, Aufgaben, Meilensteine und Risiken',
      descriptionEn: 'Status reports, tasks, milestones and risks',
      sampleDe: 'Jeden Freitag werden Projektupdates aus den Teams gesammelt, offene Aufgaben und Meilensteine abgeglichen, Risiken zusammengefasst und ein Statusbericht für den Lenkungskreis vorbereitet.',
      sampleEn: 'Every Friday, project updates are collected from teams, open tasks and milestones are reconciled, risks are summarized and a status report is prepared for the steering committee.'
    },
    {
      id: 'operations', icon: '⌂',
      nameDe: 'Facility & Verwaltung', nameEn: 'Facilities & Administration',
      descriptionDe: 'Wartungen, Dokumente, interne Services und Abläufe',
      descriptionEn: 'Maintenance, documents, internal services and administration',
      sampleDe: 'Wartungsanfragen aus den Standorten werden zentral erfasst, nach Dringlichkeit und Gewerke sortiert, an Dienstleister verteilt und bis zur dokumentierten Erledigung nachverfolgt.',
      sampleEn: 'Maintenance requests from all sites are captured centrally, categorized by urgency and trade, assigned to service providers and tracked until completion is documented.'
    }
  ];

  private readonly de: Record<string, string> = {
    brand: 'FlowPilot', product: 'AI Process Automation Engine',
    workspace: 'DEMO-ARBEITSBEREICH', language: 'Sprache',
    navOverview: 'Übersicht', navIndustries: 'Geschäftsbereiche', navBuilder: 'Prozess erstellen',
    navData: 'Datenwerkstatt', navSecurity: 'Kontrolle & Freigaben',
    activeWorkspace: 'Arbeitsbereich aktiv', systemReady: 'System bereit',
    heroEyebrow: 'INTELLIGENTE PROZESSAUTOMATISIERUNG',
    heroTitle: 'Weniger Routine. Mehr Wirkung.',
    heroCopy: 'Beschreiben Sie Ihre Abläufe. FlowPilot erkennt Potenziale und entwirft kontrollierbare Workflows – mit Python-Regeln und KI.',
    startAnalysis: 'Analyse starten', exploreAreas: 'Geschäftsbereiche entdecken',
    pillHybrid: 'Hybrid: Python + KI', pillApproval: 'Freigaben bleiben unter Kontrolle', pillNoCode: 'Ohne Programmierung starten',
    metricIndustries: 'Geschäftsbereiche', metricEngines: 'Analysemodi', metricData: 'Datenformate',
    industriesEyebrow: 'BRANCHEN & FACHBEREICHE', industriesTitle: 'Wo möchten Sie automatisieren?',
    industriesCopy: 'Wählen Sie einen Bereich. Ein passendes Praxisbeispiel wird direkt in den Prozess-Editor übernommen.',
    selected: 'Ausgewählt', useExample: 'Beispiel verwenden', allAreas: 'Freie Beschreibung',
    builderEyebrow: 'WORKFLOW DESIGNER', builderTitle: 'Beschreiben Sie Ihren Prozess',
    builderCopy: 'Starten Sie mit einem Beispiel oder schildern Sie Ihren eigenen Ablauf. Die Analyse erstellt daraus einen strukturierten Workflow-Entwurf.',
    selectedArea: 'Geschäftsbereich', strategy: 'Analysemethode',
    strategyAuto: 'Automatisch · Hybrid', strategyRules: 'Python-Regeln · kostenlos', strategyLlm: 'KI-Analyse · API-Guthaben',
    descriptionLabel: 'Wie läuft der Prozess heute ab?',
    descriptionHint: 'Beschreiben Sie Auslöser, beteiligte Personen, Datenquellen, manuelle Schritte und gewünschtes Ergebnis.',
    descriptionPlaceholder: 'Beispiel: Jeden Montag erhält unser Einkauf Excel-Listen von Lieferanten. Die Daten werden geprüft, mit offenen Bestellungen abgeglichen und als Abweichungsbericht vorbereitet …',
    chars: 'Zeichen', analyze: 'Prozess analysieren', analyzing: 'Analyse läuft …',
    dataEyebrow: 'PYTHON DATA WORKSPACE', dataTitle: 'Daten prüfen & verstehen',
    dataCopy: 'Laden Sie eine CSV- oder Excel-Datei hoch. Python erkennt Spalten, fehlende Werte und Duplikate und erstellt eine bereinigte Vorschau – ohne KI-API-Kosten.',
    chooseFile: 'Datei auswählen', fileHint: 'CSV oder XLSX · maximal 10 MB · bei Excel wird das erste Tabellenblatt gelesen',
    noFile: 'Noch keine Datei ausgewählt', processFile: 'Datei analysieren', processing: 'Datei wird verarbeitet …',
    rows: 'Zeilen', cleanRows: 'Bereinigte Zeilen', columns: 'Spalten', duplicates: 'Duplikate', emptyRows: 'Leere Zeilen',
    columnProfiles: 'Spaltenprofile', column: 'Spalte', dataType: 'Datentyp', missing: 'Fehlende Werte', unique: 'Eindeutig', numeric: 'Kennzahlen',
    preview: 'Bereinigte Datenvorschau', firstRows: 'Erste', processingLog: 'Verarbeitungsschritte',
    noApiCost: 'Keine API-Kosten', dataNotice: 'Die Datei wird nur im Arbeitsspeicher verarbeitet und nicht gespeichert.',
    truncated: 'Die Datei enthält mehr als 20.000 Datenzeilen. Die Analyse umfasst die ersten 20.000 nicht leeren Zeilen.',
    resultEyebrow: 'ANALYSEERGEBNIS', resultTitle: 'Ihr Prozess auf einen Blick',
    automationPotential: 'Automatisierungspotenzial', estimate: 'Schätzung anhand erkannter Prozessmerkmale',
    summary: 'Zusammenfassung', currentProcess: 'Heutiger Ablauf', opportunities: 'Automatisierungschancen',
    workflow: 'Workflow-Entwurf', draft: 'Entwurf', trigger: 'Auslöser', integrations: 'Geplante Integrationen',
    planned: 'Geplant', approval: 'Menschliche Freigabe', required: 'Erforderlich', recommended: 'Empfohlen',
    risks: 'Risiken & Kontrollen', questions: 'Offene Fragen', assumptions: 'Annahmen zur Bestätigung',
    execution: 'KONTROLLIERTE AUSFÜHRUNG', executionTitle: 'Freigabeprozess testen',
    simulation: 'Nur Simulation', executionCopy: 'Erstellen Sie eine Freigabeanfrage. Es wird nichts ausgeführt, bevor eine Person zustimmt. Auch danach werden nur Schritte simuliert.',
    createRequest: 'Freigabeanfrage erstellen', creating: 'Anfrage wird erstellt …',
    approveRun: 'Freigeben & simulieren', reject: 'Ablehnen', awaiting: 'Wartet auf Freigabe',
    completed: 'Abgeschlossen', rejected: 'Abgelehnt', executionId: 'Ausführungs-ID',
    approvalRecorded: 'Freigabe gespeichert. Alle Schritte wurden erfolgreich simuliert. Es wurde keine externe Nachricht versendet.',
    rejectionRecorded: 'Die Anfrage wurde abgelehnt. Es wurden keine Workflow-Schritte ausgeführt.',
    reviewBefore: 'Bitte prüfen Sie den Workflow. Die Freigabe startet nur eine Simulation und kontaktiert keine externen Systeme.',
    humanGate: 'Freigabeschritt', noSignals: 'Keine bekannten Merkmale erkannt.',
    noIntegrations: 'Bisher wurden keine externen Integrationen erkannt.',
    noActivities: 'Keine bekannten Aktivitäten erkannt', noFiles: 'Keine Dateiformate erkannt',
    notDetected: 'Nicht erkannt', frequency: 'Häufigkeit', sources: 'Datenquellen', delivery: 'Ausgabekanäle',
    detectedData: 'Erkannte Prozessdaten', ruleExtraction: 'REGELBASIERTE ERKENNUNG',
    inferenceNote: 'Dies sind regelbasierte Schlussfolgerungen aus der Beschreibung – keine verifizierten Verbindungen oder ausgelesenen Dateien.',
    routePython: 'Python ausgewählt', routeLlm: 'KI ausgewählt', complexity: 'Hinweise für eine vertiefte Analyse',
    missingKey: 'API-Schlüssel fehlt', missingKeyText: 'KI-Analyse wurde angefordert, aber der Backend-API-Schlüssel ist nicht konfiguriert. Es wurden stattdessen Python-Regeln verwendet.',
    engineNote: 'Analysehinweis', impactHigh: 'Hohe Wirkung', impactMedium: 'Mittlere Wirkung', impactLow: 'Geringe Wirkung',
    footer: 'FlowPilot ist ein Portfolio-Prototyp. Integrationen sind derzeit nicht verbunden; Workflow-Ausführungen laufen ausschließlich im Simulationsmodus.',
    errorAnalysis: 'Der Prozess konnte nicht analysiert werden. Bitte prüfen Sie die Backend-Verbindung.',
    errorUpload: 'Die Datei konnte nicht verarbeitet werden. Bitte prüfen Sie das Format.',
    errorRequest: 'Die Freigabeanfrage konnte nicht erstellt werden.',
    errorApprove: 'Die Freigabe konnte nicht gespeichert werden.',
    errorReject: 'Die Ablehnung konnte nicht gespeichert werden.',
    qualityScore: 'Datenqualität', min: 'Min', average: 'Ø', max: 'Max',
    uploadSelected: 'Ausgewählte Datei', domainGeneral: 'Allgemeiner Prozess'
  };

  private readonly en: Record<string, string> = {
    brand: 'FlowPilot', product: 'AI Process Automation Engine',
    workspace: 'DEMO WORKSPACE', language: 'Language',
    navOverview: 'Overview', navIndustries: 'Business areas', navBuilder: 'Process builder',
    navData: 'Data workspace', navSecurity: 'Governance & approvals',
    activeWorkspace: 'Workspace active', systemReady: 'System ready',
    heroEyebrow: 'INTELLIGENT PROCESS AUTOMATION',
    heroTitle: 'Less routine. More impact.',
    heroCopy: 'Describe how work gets done. FlowPilot finds opportunities and designs controlled workflows with Python rules and AI.',
    startAnalysis: 'Start analysis', exploreAreas: 'Explore business areas',
    pillHybrid: 'Hybrid: Python + AI', pillApproval: 'Human approvals stay in control', pillNoCode: 'Start without coding',
    metricIndustries: 'Business areas', metricEngines: 'Analysis modes', metricData: 'Data formats',
    industriesEyebrow: 'INDUSTRIES & FUNCTIONS', industriesTitle: 'Where would you like to automate?',
    industriesCopy: 'Choose an area. A practical example will be loaded directly into the process builder.',
    selected: 'Selected', useExample: 'Use example', allAreas: 'Free description',
    builderEyebrow: 'WORKFLOW DESIGNER', builderTitle: 'Describe your process',
    builderCopy: 'Start with an example or describe your own workflow. The analysis turns it into a structured workflow proposal.',
    selectedArea: 'Business area', strategy: 'Analysis strategy',
    strategyAuto: 'Automatic · Hybrid', strategyRules: 'Python rules · no API cost', strategyLlm: 'AI analysis · API credits',
    descriptionLabel: 'How does the process work today?',
    descriptionHint: 'Describe the trigger, people involved, data sources, manual steps and expected outcome.',
    descriptionPlaceholder: 'Example: Every Monday, Procurement receives Excel lists from suppliers. The data is checked, matched against open purchase orders and prepared as an exception report …',
    chars: 'characters', analyze: 'Analyze process', analyzing: 'Analyzing …',
    dataEyebrow: 'PYTHON DATA WORKSPACE', dataTitle: 'Inspect & understand your data',
    dataCopy: 'Upload a CSV or Excel file. Python profiles columns, missing values and duplicates and creates a cleaned preview — with no AI API cost.',
    chooseFile: 'Choose file', fileHint: 'CSV or XLSX · maximum 10 MB · Excel reads the first worksheet',
    noFile: 'No file selected yet', processFile: 'Analyze file', processing: 'Processing file …',
    rows: 'Rows', cleanRows: 'Clean rows', columns: 'Columns', duplicates: 'Duplicates', emptyRows: 'Empty rows',
    columnProfiles: 'Column profiles', column: 'Column', dataType: 'Data type', missing: 'Missing values', unique: 'Unique', numeric: 'Numeric summary',
    preview: 'Cleaned data preview', firstRows: 'First', processingLog: 'Processing steps',
    noApiCost: 'No API cost', dataNotice: 'The file is processed in memory only and is not stored.',
    truncated: 'The file contains more than 20,000 data rows. The analysis covers the first 20,000 non-empty rows.',
    resultEyebrow: 'ANALYSIS RESULT', resultTitle: 'Your process at a glance',
    automationPotential: 'Automation potential', estimate: 'Estimate based on detected process characteristics',
    summary: 'Summary', currentProcess: 'Current process', opportunities: 'Automation opportunities',
    workflow: 'Workflow proposal', draft: 'Draft', trigger: 'Trigger', integrations: 'Planned integrations',
    planned: 'Planned', approval: 'Human approval', required: 'Required', recommended: 'Recommended',
    risks: 'Risks & controls', questions: 'Open questions', assumptions: 'Assumptions to confirm',
    execution: 'CONTROLLED EXECUTION', executionTitle: 'Test the approval lifecycle',
    simulation: 'Simulation only', executionCopy: 'Create an approval request. Nothing runs before a person approves it. Even after approval, workflow steps are simulated only.',
    createRequest: 'Create approval request', creating: 'Creating request …',
    approveRun: 'Approve & run simulation', reject: 'Reject', awaiting: 'Awaiting approval',
    completed: 'Completed', rejected: 'Rejected', executionId: 'Execution ID',
    approvalRecorded: 'Approval recorded. All steps were simulated successfully. No external message was sent.',
    rejectionRecorded: 'The request was rejected. No workflow steps were executed.',
    reviewBefore: 'Review the workflow. Approval starts a simulation only and does not contact external systems.',
    humanGate: 'Human gate', noSignals: 'No known signals detected.',
    noIntegrations: 'No external integrations detected yet.',
    noActivities: 'No known activities detected', noFiles: 'No file formats detected',
    notDetected: 'Not detected', frequency: 'Frequency', sources: 'Sources', delivery: 'Delivery channels',
    detectedData: 'Detected process data', ruleExtraction: 'RULE-BASED EXTRACTION',
    inferenceNote: 'These are rule-based inferences from the description, not verified connections or extracted file contents.',
    routePython: 'Python selected', routeLlm: 'AI selected', complexity: 'Signals requiring deeper analysis',
    missingKey: 'API key missing', missingKeyText: 'AI analysis was requested, but the backend API key is not configured. Python rules were used instead.',
    engineNote: 'Analysis note', impactHigh: 'High impact', impactMedium: 'Medium impact', impactLow: 'Low impact',
    footer: 'FlowPilot is a portfolio prototype. Integrations are not connected yet; workflow execution runs in simulation mode only.',
    errorAnalysis: 'Could not analyze the process. Please check the backend connection.',
    errorUpload: 'Could not process this file. Please check its format.',
    errorRequest: 'Could not create the approval request.',
    errorApprove: 'Could not save the approval.',
    errorReject: 'Could not save the rejection.',
    qualityScore: 'Data quality', min: 'Min', average: 'Avg', max: 'Max',
    uploadSelected: 'Selected file', domainGeneral: 'General process'
  };

  get i18n(): Record<string, string> {
    return this.language() === 'de' ? this.de : this.en;
  }

  get selectedIndustry(): Industry | undefined {
    return this.industries.find(item => item.id === this.selectedDomain());
  }

  setLanguage(language: AppLanguage) {
    const previous = this.language();
    if (previous === language) return;

    const industry = this.selectedIndustry;
    if (industry) {
      const previousExample = previous === 'de' ? industry.sampleDe : industry.sampleEn;
      if (this.description === previousExample) {
        this.description = language === 'de' ? industry.sampleDe : industry.sampleEn;
      }
    }
    this.language.set(language);

    if (this.store.analysis()) {
      this.service.analyze(this.description, this.analysisStrategy, language, this.selectedDomain());
    }
    if (this.dataResult() && this.selectedDataFile && !this.dataProcessing()) {
      this.uploadDataFile();
    }
  }

  selectIndustry(industry: Industry) {
    this.selectedDomain.set(industry.id);
    this.description = this.language() === 'de' ? industry.sampleDe : industry.sampleEn;
    this.dataError.set(null);
    this.execution.set(null);
  }

  useFreeDescription() {
    this.selectedDomain.set('general');
    this.description = '';
  }

  useExampleForCurrentLanguage() {
    const industry = this.selectedIndustry;
    if (industry) this.description = this.language() === 'de' ? industry.sampleDe : industry.sampleEn;
  }

  onDataFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    this.selectedDataFile = input.files?.item(0) ?? null;
    this.dataResult.set(null);
    this.dataError.set(null);
  }

  uploadDataFile() {
    const file = this.selectedDataFile;
    if (!file || this.dataProcessing()) return;

    this.dataProcessing.set(true);
    this.dataError.set(null);
    this.dataResult.set(null);
    this.api.uploadDataFile(file, this.language()).subscribe({
      next: result => {
        this.dataResult.set(result);
        this.dataProcessing.set(false);
      },
      error: error => {
        this.dataError.set(error?.status === 413 ? (this.language() === 'de' ? 'Die Datei ist größer als das Limit von 10 MB.' : 'The file exceeds the 10 MB size limit.') : this.i18n.errorUpload);
        this.dataProcessing.set(false);
      }
    });
  }

  analyze() {
    this.execution.set(null);
    this.executionError.set(null);
    this.store.setDescription(this.description);
    this.service.analyze(this.description, this.analysisStrategy, this.language(), this.selectedDomain());
  }

  startExecution() {
    const workflow = this.store.analysis()?.proposedWorkflow;
    if (!workflow || this.executionLoading()) return;

    this.executionLoading.set(true);
    this.executionError.set(null);
    this.api.startExecution(workflow).subscribe({
      next: result => {
        this.execution.set(result);
        this.executionLoading.set(false);
      },
      error: error => {
        this.executionError.set(this.i18n.errorRequest);
        this.executionLoading.set(false);
      }
    });
  }

  approveExecution() {
    const current = this.execution();
    if (!current || current.status !== 'awaiting_approval' || this.executionLoading()) return;

    this.executionLoading.set(true);
    this.executionError.set(null);
    const note = this.language() === 'de' ? 'Über FlowPilot freigegeben.' : 'Approved from FlowPilot.';
    this.api.approveExecution(current.id, note).subscribe({
      next: result => {
        this.execution.set(result);
        this.executionLoading.set(false);
      },
      error: error => {
        this.executionError.set(this.i18n.errorApprove);
        this.executionLoading.set(false);
      }
    });
  }

  rejectExecution() {
    const current = this.execution();
    if (!current || current.status !== 'awaiting_approval' || this.executionLoading()) return;

    this.executionLoading.set(true);
    this.executionError.set(null);
    const note = this.language() === 'de' ? 'Über FlowPilot abgelehnt.' : 'Rejected from FlowPilot.';
    this.api.rejectExecution(current.id, note).subscribe({
      next: result => {
        this.execution.set(result);
        this.executionLoading.set(false);
      },
      error: error => {
        this.executionError.set(this.i18n.errorReject);
        this.executionLoading.set(false);
      }
    });
  }

  formatNumber(value: number): string {
    return new Intl.NumberFormat(this.language() === 'de' ? 'de-DE' : 'en-US').format(value);
  }

  formatValue(value: string | number | boolean | null | undefined): string {
    if (value === null || value === undefined || value === '') return '—';
    return typeof value === 'number'
      ? new Intl.NumberFormat(this.language() === 'de' ? 'de-DE' : 'en-US', { maximumFractionDigits: 3 }).format(value)
      : String(value);
  }
}
