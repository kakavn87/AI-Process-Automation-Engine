import { Component, effect, inject, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';
import { AuthService } from '../../../../core/services/auth.service';
import { IntegrationReadiness, TabularDataResult, WorkflowSession } from '../../../../core/models/api.models';
import { ProcessStore } from '../../process.store';
import { ProcessService } from '../../process.service';
import { WorkflowSessionPageComponent } from '../../../workflow-session/workflow-session-page.component';

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
  imports: [FormsModule, WorkflowSessionPageComponent, DatePipe],
  templateUrl: './process-page.component.html'
})
export class ProcessPageComponent implements OnInit {
  readonly store = inject(ProcessStore);
  readonly auth = inject(AuthService);
  private readonly service = inject(ProcessService);
  private readonly api = inject(ApiService);


  readonly language = signal<AppLanguage>('de');
  readonly selectedDomain = signal('general');
  readonly examplesExpanded = signal(false);
  readonly dataResult = signal<TabularDataResult | null>(null);
  readonly dataProcessing = signal(false);
  readonly dataError = signal<string | null>(null);
  readonly integrationReadiness = signal<IntegrationReadiness | null>(null);
  readonly integrationLoading = signal(false);
  readonly integrationError = signal<string | null>(null);
  readonly workflowSession = signal<WorkflowSession | null>(null);
  readonly workspaceCreating = signal(false);
  readonly workspaceCreateError = signal<string | null>(null);
  readonly workspaceCreateSuccess = signal<string | null>(null);
  newWorkspaceName = '';
  readonly invitationLoading = signal(false);
  readonly invitationError = signal<string | null>(null);
  readonly invitationResult = signal<{
    email: string;
    role: string;
    invitation_token: string;
    expires_at: string;
  } | null>(null);
  workspaceInviteEmail = '';
  workspaceInviteRole: 'admin' | 'member' | 'approver' = 'member';

  selectedDataFile: File | null = null;
  processFiles: File[] = [];
  readonly processFileError = signal<string | null>(null);
  description = '';
  analysisStrategy: AnalysisStrategy = 'auto';

  constructor() {
    effect(() => {
      const analysis = this.store.analysis();
      if (!analysis || typeof document === 'undefined') return;

      setTimeout(() => {
        document.getElementById('results')?.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }, 0);
    });
  }

  ngOnInit() {
    this.refreshIntegrationReadiness();
  }

  refreshIntegrationReadiness() {
    this.integrationLoading.set(true);
    this.integrationError.set(null);
    this.api.getIntegrationReadiness().subscribe({
      next: result => {
        this.integrationReadiness.set(result);
        this.integrationLoading.set(false);
      },
      error: () => {
        this.integrationError.set(
          this.language() === 'de'
            ? 'Integrationsstatus konnte nicht geladen werden.'
            : 'Could not load integration status.'
        );
        this.integrationLoading.set(false);
      }
    });
  }

  createWorkspace(): void {
    const name = this.newWorkspaceName.trim();
    if (!name || this.workspaceCreating() || !this.auth.isAuthenticated()) return;

    this.workspaceCreating.set(true);
    this.workspaceCreateError.set(null);
    this.workspaceCreateSuccess.set(null);
    this.auth.createWorkspace(name).subscribe({
      next: () => {
        this.newWorkspaceName = '';
        this.workspaceCreateSuccess.set(this.language() === 'de'
          ? 'Arbeitsbereich erstellt. Sie sind jetzt im neuen Arbeitsbereich angemeldet.'
          : 'Workspace created. You are now signed in to the new workspace.');
        this.workspaceCreating.set(false);
        this.invitationResult.set(null);
      },
      error: response => {
        const detail = response?.error?.detail;
        this.workspaceCreateError.set(typeof detail === 'string'
          ? detail
          : (this.language() === 'de'
            ? 'Der Arbeitsbereich konnte nicht erstellt werden.'
            : 'Could not create the workspace.'));
        this.workspaceCreating.set(false);
      }
    });
  }

  canManageWorkspace(): boolean {
    const role = this.auth.user()?.role;
    return this.auth.isAuthenticated() && (role === 'owner' || role === 'admin');
  }

  createWorkspaceInvitation(): void {
    const email = this.workspaceInviteEmail.trim().toLowerCase();
    if (!email || this.invitationLoading() || !this.canManageWorkspace()) return;

    this.invitationLoading.set(true);
    this.invitationError.set(null);
    this.invitationResult.set(null);
    this.api.createWorkspaceInvitation(email, this.workspaceInviteRole).subscribe({
      next: result => {
        this.invitationResult.set(result);
        this.workspaceInviteEmail = '';
        this.invitationLoading.set(false);
      },
      error: response => {
        const detail = response?.error?.detail;
        this.invitationError.set(typeof detail === 'string'
          ? detail
          : (this.language() === 'de'
            ? 'Die Einladung konnte nicht erstellt werden.'
            : 'Could not create the invitation.'));
        this.invitationLoading.set(false);
      }
    });
  }

  integrationStatusLabel(status: string): string {
    if (this.language() !== 'de') return status.replaceAll('_', ' ');
    const labels: Record<string, string> = {
      configured: 'Konfiguriert',
      not_configured: 'Nicht konfiguriert',
      ready: 'Bereit',
      setup_required: 'Einrichtung erforderlich',
      planned: 'Geplant',
      disabled: 'Deaktiviert',
      connected: 'Verbunden',
      not_connected: 'Nicht verbunden',
      unavailable: 'Nicht verfügbar',
      enabled: 'Aktiv',
      active: 'Aktiv',
      missing: 'Fehlt'
    };
    return labels[status.toLowerCase()] ?? status.replaceAll('_', ' ');
  }

  onWorkflowSessionChange(session: WorkflowSession | null) {
    this.workflowSession.set(session);
  }

  workflowStepState(step: number): 'complete' | 'active' | 'pending' | 'error' {
    const status = this.workflowSession()?.status;

    if (step === 1) return !this.store.loading() && this.store.analysis() ? 'complete' : 'active';
    if (!status) return 'pending';

    if (step === 2) {
      if (status === 'needs_input') return 'active';
      if (['processing', 'ready_for_approval', 'awaiting_approval', 'completed', 'rejected', 'failed'].includes(status)) return 'complete';
      return 'pending';
    }
    if (step === 3) {
      if (status === 'processing') return 'active';
      if (['ready_for_approval', 'awaiting_approval', 'completed', 'rejected'].includes(status)) return 'complete';
      return status === 'failed' ? 'error' : 'pending';
    }
    if (step === 4) {
      if (status === 'ready_for_approval' || status === 'awaiting_approval') return 'active';
      if (status === 'completed' || status === 'rejected') return 'complete';
      return 'pending';
    }
    if (step === 5) {
      if (status === 'completed' || status === 'rejected') return 'complete';
      return 'pending';
    }
    return 'pending';
  }

  workflowStepAvailable(step: number): boolean {
    return step === 1 || this.workflowSession() !== null;
  }

  workflowStepMarker(step: number): string {
    const state = this.workflowStepState(step);
    return state === 'complete' ? '✓' : state === 'active' ? '●' : state === 'error' ? '!' : '·';
  }

  workflowStepHint(step: number): string {
    const status = this.workflowSession()?.status;
    const state = this.workflowStepState(step);
    if (step === 1) {
      return state === 'complete'
        ? (this.language() === 'de' ? 'Analyse gespeichert' : 'Analysis saved')
        : (this.language() === 'de' ? 'Prozess beschreiben' : 'Describe your process');
    }
    if (step === 2) {
      if (status === 'needs_input') return this.language() === 'de' ? 'Ihre Angaben werden benötigt' : 'Your input is needed';
      return state === 'complete'
        ? (this.language() === 'de' ? 'Klärung abgeschlossen' : 'Clarification complete')
        : (this.language() === 'de' ? 'Nach der Analyse' : 'After analysis');
    }
    if (step === 3) {
      if (status === 'processing') return this.language() === 'de' ? 'Python prüft die Angaben' : 'Python validates the answers';
      if (state === 'complete') return this.language() === 'de' ? 'Workflow vorbereitet' : 'Workflow prepared';
      if (state === 'error') return this.language() === 'de' ? 'Verarbeitung fehlgeschlagen' : 'Processing failed';
      return this.language() === 'de' ? 'Nach der Klärung' : 'After clarification';
    }
    if (step === 4) {
      if (status === 'ready_for_approval') return this.language() === 'de' ? 'Ihre Prüfung erforderlich' : 'Your review is required';
      if (status === 'awaiting_approval') return this.language() === 'de' ? 'Wartet auf Entscheidung' : 'Waiting for decision';
      if (state === 'complete') return this.language() === 'de' ? 'Entscheidung dokumentiert' : 'Decision recorded';
      return this.language() === 'de' ? 'Nach der Verarbeitung' : 'After processing';
    }
    if (step === 5) {
      return state === 'complete'
        ? (this.language() === 'de' ? 'Nutzung & Kosten erfasst' : 'Usage & costs recorded')
        : (this.language() === 'de' ? 'Nach Workflow-Abschluss' : 'After workflow completion');
    }
    return '';
  }

  navigateToWorkflowStep(step: number) {
    if (!this.workflowStepAvailable(step) || typeof document === 'undefined') return;
    const targetId = step === 1 ? 'builder' : `workflow-step-${step}`;
    const target = document.getElementById(targetId)
      ?? document.getElementById('workflow-session')
      ?? document.getElementById('results');
    target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

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

  private readonly de = {
    brand: 'AI Process Optimierung', product: 'KI-gestützte Prozessoptimierung',
    workspace: 'DEMO-ARBEITSBEREICH', language: 'Sprache',
    navOverview: 'Start', navIndustries: 'Beispiele', navBuilder: 'Prozess erstellen',
    navData: 'Datenwerkstatt', navSecurity: 'Kontrolle & Freigaben',
    activeWorkspace: 'Arbeitsbereich aktiv', systemReady: 'System bereit',
    heroEyebrow: 'UNIVERSELLE KI-PROZESSAUTOMATISIERUNG',
    heroTitle: 'Ein KI-Kern. Jeder Prozess.',
    heroCopy: 'Beschreiben Sie jeden Geschäftsprozess – auch Nischen- und Spezialabläufe. AI Process Optimierung versteht die Aufgabe, strukturiert den Workflow und nutzt Python für Daten, Regeln und sichere Ausführung.',
    startAnalysis: 'Analyse starten', exploreAreas: 'Geschäftsbereiche entdecken',
    pillHybrid: 'Hybrid: Python + KI', pillApproval: 'Freigaben bleiben unter Kontrolle', pillNoCode: 'Ohne Programmierung starten',
    metricIndustries: 'Geschäftsbereiche', metricEngines: 'Analysemodi', metricData: 'Datenformate',
    industriesEyebrow: 'OPTIONAL · MIT VORLAGE STARTEN', industriesTitle: 'Ein Beispiel auswählen',
    industriesCopy: 'Wählen Sie einen Bereich, um eine Beispielbeschreibung einzufügen. Sie können den Text anschließend frei anpassen.',
    selected: 'Ausgewählt', useExample: 'Beispiel verwenden', allAreas: 'Freie Beschreibung',
    builderEyebrow: 'SCHRITT 1 · PROZESS BESCHREIBEN', builderTitle: 'Welchen Prozess möchten Sie automatisieren?',
    builderCopy: 'Beschreiben Sie den Ablauf in wenigen Sätzen. AI Process Optimierung erkennt manuelle Schritte, Datenquellen und mögliche Automatisierungen und erstellt daraus einen prüfbaren Workflow-Entwurf.',
    selectedArea: 'Geschäftsbereich', strategy: 'Analysemethode',
    strategyAuto: 'Automatisch · KI zuerst', strategyRules: 'Python-Regeln · kostenlos', strategyLlm: 'KI-Analyse · API-Guthaben',
    descriptionLabel: 'Wie läuft der Prozess heute ab?',
    descriptionHint: 'Nennen Sie den Auslöser, die beteiligten Personen, verwendete Dateien oder Systeme und das gewünschte Ergebnis.',
    descriptionPlaceholder: 'Beispiel: Jeden Montag erhält der Einkauf Excel-Listen von Lieferanten. Die Daten werden geprüft, mit offenen Bestellungen abgeglichen und ein Bericht mit Abweichungen vorbereitet …',
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
    automationPotential: 'Automatisierungspotenzial', estimate: 'Indikative Einschätzung – kein garantierter Anteil eingesparter Arbeitszeit.', estimateAi: 'KI-Einschätzung des Automatisierungspotenzials.', estimatePython: 'Näherung anhand erkannter Prozessschritte; unbekannte Begriffe können unentdeckt bleiben.',
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
    footer: 'AI Process Optimierung ist ein Portfolio-Prototyp. Integrationen sind derzeit nicht verbunden; Workflow-Ausführungen laufen ausschließlich im Simulationsmodus.',
    errorAnalysis: 'Der Prozess konnte nicht analysiert werden. Bitte prüfen Sie die Backend-Verbindung.',
    errorUpload: 'Die Datei konnte nicht verarbeitet werden. Bitte prüfen Sie das Format.',
    errorRequest: 'Die Freigabeanfrage konnte nicht erstellt werden.',
    errorApprove: 'Die Freigabe konnte nicht gespeichert werden.',
    errorReject: 'Die Ablehnung konnte nicht gespeichert werden.',
    qualityScore: 'Datenqualität', min: 'Min', average: 'Ø', max: 'Max',
    uploadSelected: 'Ausgewählte Datei', universalModel: 'UNIVERSELLES PROZESSMODELL', processGoal: 'Prozessziel', actors: 'Beteiligte Rollen', inputs: 'Eingaben', systems: 'Systeme', businessRules: 'Geschäftsregeln', exceptionPaths: 'Ausnahmen & Sonderfälle', outputs: 'Ergebnisse', successMetrics: 'Erfolgskennzahlen', domainGeneral: 'Freier Prozess / neue Domäne'
  };

  private readonly en = {
    brand: 'AI Process Optimierung', product: 'AI-powered process optimization',
    workspace: 'DEMO WORKSPACE', language: 'Language',
    navOverview: 'Start', navIndustries: 'Examples', navBuilder: 'Process builder',
    navData: 'Data workspace', navSecurity: 'Governance & approvals',
    activeWorkspace: 'Workspace active', systemReady: 'System ready',
    heroEyebrow: 'AI-POWERED PROCESS OPTIMIZATION',
    heroTitle: 'One AI. Every business process.',
    heroCopy: 'Describe any business process, including niche and specialist workflows. AI Process Optimierung understands the task, structures the workflow and uses Python for data, rules and safe execution.',
    startAnalysis: 'Start analysis', exploreAreas: 'Explore business areas',
    pillHybrid: 'Hybrid: Python + AI', pillApproval: 'Human approvals stay in control', pillNoCode: 'Start without coding',
    metricIndustries: 'Business areas', metricEngines: 'Analysis modes', metricData: 'Data formats',
    industriesEyebrow: 'OPTIONAL · START WITH AN EXAMPLE', industriesTitle: 'Choose an example',
    industriesCopy: 'Choose a business area to insert a sample description. You can then adapt the text to match your own process.',
    selected: 'Selected', useExample: 'Use example', allAreas: 'Free description',
    builderEyebrow: 'STEP 1 · DESCRIBE YOUR PROCESS', builderTitle: 'What process would you like to automate?',
    builderCopy: 'Describe the current process in a few sentences. AI Process Optimierung identifies manual steps, data sources and automation opportunities, then creates a workflow draft you can review.',
    selectedArea: 'Business area', strategy: 'Analysis strategy',
    strategyAuto: 'Automatic · AI first', strategyRules: 'Python rules · no API cost', strategyLlm: 'AI analysis · API credits',
    descriptionLabel: 'How does the process work today?',
    descriptionHint: 'Include the trigger, people involved, files or systems used, and the desired result.',
    descriptionPlaceholder: 'Example: Every Monday, Procurement receives Excel lists from suppliers. The data is checked against open purchase orders and a report of exceptions is prepared …',
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
    automationPotential: 'Automation potential', estimate: 'Indicative estimate — not a guaranteed share of working time saved.', estimateAi: 'AI estimate of the process automation potential.', estimatePython: 'Approximation from detected process steps; unknown terms may not be recognized.',
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
    footer: 'AI Process Optimierung is a portfolio prototype. Integrations are not connected yet; workflow execution runs in simulation mode only.',
    errorAnalysis: 'Could not analyze the process. Please check the backend connection.',
    errorUpload: 'Could not process this file. Please check its format.',
    errorRequest: 'Could not create the approval request.',
    errorApprove: 'Could not save the approval.',
    errorReject: 'Could not save the rejection.',
    qualityScore: 'Data quality', min: 'Min', average: 'Avg', max: 'Max',
    uploadSelected: 'Selected file', universalModel: 'UNIVERSAL PROCESS MODEL', processGoal: 'Process goal', actors: 'People & roles', inputs: 'Inputs', systems: 'Systems', businessRules: 'Business rules', exceptionPaths: 'Exceptions & edge cases', outputs: 'Outputs', successMetrics: 'Success metrics', domainGeneral: 'Free process / new domain'
  };

  get i18n() {
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
      this.service.analyze(this.description, this.analysisStrategy, language, this.selectedDomain(), this.processFiles);
    }
    if (this.dataResult() && this.selectedDataFile && !this.dataProcessing()) {
      this.uploadDataFile();
    }
  }

  toggleIndustryExamples() {
    this.examplesExpanded.update(expanded => !expanded);
  }

  selectIndustry(industry: Industry) {
    this.examplesExpanded.set(false);
    this.selectedDomain.set(industry.id);
    this.description = this.language() === 'de' ? industry.sampleDe : industry.sampleEn;
    this.dataError.set(null);
  }

  useFreeDescription() {
    this.examplesExpanded.set(false);
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

  onProcessFilesSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const selected = Array.from(input.files ?? []);
    const allowed = /\.(pdf|docx|pptx|xlsx|csv|txt|md|png|jpe?g|webp|drawio|bpmn|xml|svg)$/i;
    const combined = [...this.processFiles, ...selected];

    if (combined.length > 8) {
      this.processFileError.set(this.language() === 'de'
        ? 'Es sind maximal 8 Dateien pro Analyse erlaubt.'
        : 'A maximum of 8 files can be added to one analysis.');
    } else if (combined.some(file => !allowed.test(file.name))) {
      this.processFileError.set(this.language() === 'de'
        ? 'Ein Dateiformat wird nicht unterstützt.'
        : 'One of the selected file types is not supported.');
    } else if (combined.some(file => file.size > 10 * 1024 * 1024)) {
      this.processFileError.set(this.language() === 'de'
        ? 'Jede Datei darf höchstens 10 MB groß sein.'
        : 'Each file must be 10 MB or smaller.');
    } else if (combined.reduce((sum, file) => sum + file.size, 0) > 25 * 1024 * 1024) {
      this.processFileError.set(this.language() === 'de'
        ? 'Die Gesamtgröße darf 25 MB nicht überschreiten.'
        : 'The combined upload size must not exceed 25 MB.');
    } else {
      this.processFiles = combined;
      this.processFileError.set(null);
    }
    input.value = '';
  }

  removeProcessFile(index: number) {
    this.processFiles = this.processFiles.filter((_, current) => current !== index);
    this.processFileError.set(null);
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
    this.workflowSession.set(null);
    this.store.setDescription(this.description);
    this.service.analyze(this.description, this.analysisStrategy, this.language(), this.selectedDomain(), this.processFiles);
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
