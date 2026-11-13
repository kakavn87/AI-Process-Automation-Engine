import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import {
  AIUsageSummary,
  ApprovalExecution,
  LiveExecutionReadiness,
  WorkflowSession
} from '../../core/models/api.models';

@Component({
  selector: 'app-workflow-session-page',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './workflow-session-page.component.html',
  styleUrl: './workflow-session-page.component.scss'
})
export class WorkflowSessionPageComponent implements OnInit, OnChanges {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(ApiService);

  readonly session = signal<WorkflowSession | null>(null);
  readonly execution = signal<ApprovalExecution | null>(null);
  readonly usage = signal<AIUsageSummary | null>(null);
  readonly liveReadiness = signal<LiveExecutionReadiness | null>(null);
  readonly liveConfirmed = signal(false);
  readonly liveToken = signal('');
  readonly liveLoading = signal(false);
  readonly answerValues = signal<Record<string, string | boolean>>({});
  readonly loading = signal(false);
  readonly submitting = signal(false);
  readonly executionLoading = signal(false);
  readonly error = signal<string | null>(null);

  @Input() sessionId = '';
  @Input() embedded = false;
  @Output() sessionChange = new EventEmitter<WorkflowSession | null>();

  private activeSessionId = '';
  private initialized = false;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['sessionId'] && this.initialized && this.sessionId &&
        this.sessionId !== this.activeSessionId) {
      this.activeSessionId = this.sessionId;
      this.session.set(null);
      this.sessionChange.emit(null);
      this.execution.set(null);
      this.usage.set(null);
      this.loadSession();
    }
  }

  ngOnInit(): void {
    this.initialized = true;
    if (this.sessionId) {
      this.activeSessionId = this.sessionId;
      this.loadSession();
    } else {
      this.route.paramMap.subscribe(params => {
        this.activeSessionId = params.get('sessionId') ?? '';
        if (this.activeSessionId) this.loadSession();
      });
    }
    this.loadLiveReadiness();
  }

  sessionStatusLabel(status: string): string {
    if (!this.isGerman) return status.replaceAll('_', ' ');
    const labels: Record<string, string> = {
      needs_input: 'Angaben erforderlich',
      processing: 'Wird verarbeitet',
      ready_for_approval: 'Zur Freigabe bereit',
      awaiting_approval: 'Wartet auf Freigabe',
      completed: 'Abgeschlossen',
      rejected: 'Abgelehnt',
      failed: 'Fehlgeschlagen'
    };
    return labels[status] ?? status.replaceAll('_', ' ');
  }

  eventStatusLabel(status: string): string {
    if (!this.isGerman) return status.replaceAll('_', ' ');
    const labels: Record<string, string> = {
      completed: 'Abgeschlossen',
      succeeded: 'Erfolgreich',
      failed: 'Fehlgeschlagen',
      rejected: 'Abgelehnt',
      pending: 'Ausstehend',
      awaiting_approval: 'Wartet auf Freigabe',
      needs_input: 'Angaben erforderlich',
      processing: 'Wird verarbeitet',
      ready_for_approval: 'Zur Freigabe bereit',
      simulated: 'Simuliert',
      recorded: 'Gespeichert',
      success: 'Erfolgreich',
      error: 'Fehler',
      llm_optimization_completed: 'KI-Optimierung abgeschlossen',
      llm_optimization_failed: 'KI-Optimierung fehlgeschlagen',
      optimization_retry_requested: 'KI-Optimierung wird erneut gestartet'
    };
    return labels[status] ?? status.replaceAll('_', ' ');
  }

  get isGerman(): boolean {
    return this.session()?.language !== 'en';
  }

  setAnswer(questionId: string, value: string | boolean): void {
    this.answerValues.update(current => ({ ...current, [questionId]: value }));
  }

  loadSession(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.getWorkflowSession(this.activeSessionId).subscribe({
      next: result => {
        this.session.set(result);
        this.sessionChange.emit(result);
        this.loading.set(false);
        this.updateUsageVisibility(result);
        if (result.relatedExecutionId) this.loadExecution(result.relatedExecutionId);
      },
      error: () => {
        this.error.set(this.isGerman
          ? 'Der Workflow konnte nicht geladen werden.'
          : 'Could not load the workflow session.');
        this.loading.set(false);
      }
    });
  }

  loadLiveReadiness(): void {
    this.api.getLiveExecutionReadiness().subscribe({
      next: result => this.liveReadiness.set(result),
      error: () => this.liveReadiness.set(null)
    });
  }

  private updateUsageVisibility(current: WorkflowSession): void {
    if (current.status === 'completed' || current.status === 'rejected') {
      this.loadUsage();
      return;
    }
    this.usage.set(null);
  }

  loadUsage(): void {
    this.api.getUsageSummary(10).subscribe({
      next: result => this.usage.set(result),
      error: () => this.usage.set(null)
    });
  }

  loadExecution(id: string): void {
    this.api.getExecution(id).subscribe({
      next: result => this.execution.set(result),
      error: () => this.error.set(this.isGerman
        ? 'Der Freigabestatus konnte nicht geladen werden.'
        : 'Could not load the approval status.')
    });
  }

  runLiveExecution(): void {
    const current = this.execution();
    if (!current || !this.liveReadiness()?.ready || !this.liveConfirmed() || !this.liveToken().trim() || this.liveLoading()) return;

    this.liveLoading.set(true);
    this.error.set(null);
    this.api.runLiveExecution(current.id, this.liveToken().trim()).subscribe({
      next: result => {
        this.execution.set(result);
        this.liveConfirmed.set(false);
        this.liveToken.set('');
        this.liveLoading.set(false);
        this.loadSession();
      },
      error: error => {
        this.error.set(error?.error?.detail || (this.isGerman
          ? 'Die externe Ausführung konnte nicht bestätigt werden.'
          : 'The external execution could not be confirmed.'));
        this.liveLoading.set(false);
        this.loadExecution(current.id);
      }
    });
  }

  submitAnswers(): void {
    const current = this.session();
    if (!current || this.submitting()) return;

    const submitted = Object.fromEntries(
      Object.entries(this.answerValues()).filter(([, value]) =>
        typeof value === 'boolean' || String(value).trim().length > 0
      )
    );
    if (!Object.keys(submitted).length) {
      this.error.set(this.isGerman
        ? 'Bitte beantworten Sie mindestens eine Frage.'
        : 'Please answer at least one question.');
      return;
    }

    this.submitting.set(true);
    this.error.set(null);
    const processing: WorkflowSession = { ...current, status: 'processing' };
    this.session.set(processing);
    this.sessionChange.emit(processing);
    this.api.submitWorkflowAnswers(current.id, submitted).subscribe({
      next: result => {
        this.session.set(result);
        this.sessionChange.emit(result);
        this.answerValues.set({});
        this.submitting.set(false);
      },
      error: error => {
        this.error.set(error?.error?.detail || (this.isGerman
          ? 'Die Antworten konnten nicht gespeichert werden.'
          : 'Could not save the answers.'));
        this.submitting.set(false);
        this.loadSession();
      }
    });
  }

  retryOptimization(): void {
    const current = this.session();
    if (!current || current.status !== 'failed' || this.submitting()) return;

    this.submitting.set(true);
    this.error.set(null);
    const processing: WorkflowSession = {
      ...current,
      status: 'processing',
      analysis: { ...current.analysis, optimizationFailure: undefined }
    };
    this.session.set(processing);
    this.sessionChange.emit(processing);
    this.api.retryWorkflowOptimization(current.id).subscribe({
      next: result => {
        this.session.set(result);
        this.sessionChange.emit(result);
        this.submitting.set(false);
      },
      error: error => {
        this.error.set(error?.error?.detail || (this.isGerman
          ? 'Die KI-Optimierung konnte nicht erneut gestartet werden.'
          : 'Could not retry the AI optimization.'));
        this.submitting.set(false);
        this.loadSession();
      }
    });
  }

  createExecution(): void {
    const current = this.session();
    if (!current || this.executionLoading()) return;

    this.executionLoading.set(true);
    this.error.set(null);
    this.api.createSessionExecution(current.id).subscribe({
      next: result => {
        this.session.set(result.session);
        this.sessionChange.emit(result.session);
        this.execution.set(result.execution);
        this.executionLoading.set(false);
      },
      error: error => {
        this.error.set(error?.error?.detail || (this.isGerman
          ? 'Die Freigabeanfrage konnte nicht erstellt werden.'
          : 'Could not create the approval request.'));
        this.executionLoading.set(false);
      }
    });
  }

  decide(approve: boolean): void {
    const current = this.execution();
    if (!current || current.status !== 'awaiting_approval' || this.executionLoading()) return;

    this.executionLoading.set(true);
    this.error.set(null);
    const note = approve
      ? (this.isGerman ? 'Über AI Process Optimierung freigegeben.' : 'Approved from AI Process Optimierung.')
      : (this.isGerman ? 'Über AI Process Optimierung abgelehnt.' : 'Rejected from AI Process Optimierung.');

    const request = approve
      ? this.api.approveExecution(current.id, note)
      : this.api.rejectExecution(current.id, note);

    request.subscribe({
      next: result => {
        this.execution.set(result);
        this.executionLoading.set(false);
        this.loadSession();
      },
      error: error => {
        this.error.set(error?.error?.detail || (this.isGerman
          ? 'Die Entscheidung konnte nicht gespeichert werden.'
          : 'Could not save the decision.'));
        this.executionLoading.set(false);
      }
    });
  }

  backToBuilder(): void {
    this.router.navigate(['/']);
  }

  stepState(step: number, status: string): 'complete' | 'active' | 'pending' | 'error' {
    if (step === 1) return 'complete';
    if (step === 2) return status === 'needs_input' ? 'active' : 'complete';
    if (step === 3) {
      if (status === 'needs_input') return 'pending';
      if (status === 'processing') return 'active';
      return status === 'failed' ? 'error' : 'complete';
    }
    if (step === 4) {
      if (status === 'ready_for_approval' || status === 'awaiting_approval') return 'active';
      if (status === 'completed' || status === 'rejected') return 'complete';
      return 'pending';
    }
    if (step === 5) return status === 'completed' || status === 'rejected' ? 'complete' : 'pending';
    return 'pending';
  }

  stepDescription(step: number, status: string): string {
    if (step === 2) {
      return this.isGerman
        ? (status === 'needs_input' ? 'Ihre Angaben werden benötigt' : 'Klärung abgeschlossen')
        : (status === 'needs_input' ? 'Your input is needed' : 'Clarification complete');
    }
    if (step === 3) {
      if (status === 'needs_input') return this.isGerman ? 'Nach den Antworten' : 'After your answers';
      if (status === 'processing') return this.isGerman ? 'LLM optimiert den Prozess; Python validiert' : 'LLM optimizes; Python validates';
      if (status === 'failed') return this.isGerman ? 'Optimierung fehlgeschlagen – Wiederholung möglich' : 'Optimization failed – retry available';
      return this.isGerman ? 'Optimierungsvorschlag bereit' : 'Optimization proposal ready';
    }
    if (step === 4) {
      if (status === 'ready_for_approval') return this.isGerman ? 'Ihre Prüfung erforderlich' : 'Your review is required';
      if (status === 'awaiting_approval') return this.isGerman ? 'Wartet auf Entscheidung' : 'Waiting for decision';
      if (status === 'completed') return this.isGerman ? 'Simulation abgeschlossen' : 'Simulation completed';
      if (status === 'rejected') return this.isGerman ? 'Anfrage abgelehnt' : 'Request rejected';
      return this.isGerman ? 'Nach der Verarbeitung' : 'After processing';
    }
    if (step === 5) {
      return status === 'completed' || status === 'rejected'
        ? (this.isGerman ? 'Nutzung & Kosten erfasst' : 'Usage & costs recorded')
        : (this.isGerman ? 'Nach Workflow-Abschluss' : 'After workflow completion');
    }
    return '';
  }

  formatNumber(value: number | null | undefined): string {
    return new Intl.NumberFormat(this.isGerman ? 'de-DE' : 'en-US').format(value ?? 0);
  }

  formatCost(value: number | null): string {
    if (value === null || value === undefined) {
      return this.isGerman ? 'Nicht verfügbar' : 'Not available';
    }
    return new Intl.NumberFormat(this.isGerman ? 'de-DE' : 'en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 6
    }).format(value);
  }

  workflowStepTypeLabel(type: string): string {
    if (!this.isGerman) return type.replaceAll('_', ' ');
    const labels: Record<string, string> = {
      trigger: 'Auslöser',
      collect: 'Daten erfassen',
      extract: 'Daten extrahieren',
      transform: 'Daten umwandeln',
      validate: 'Daten prüfen',
      generate: 'Ergebnis erstellen',
      approval: 'Freigabe',
      notify: 'Benachrichtigung',
      email: 'E-Mail versenden',
      teams: 'Teams-Nachricht',
      http: 'HTTP-Anfrage'
    };
    return labels[type] ?? type.replaceAll('_', ' ');
  }

  formatMetric(value: number | null, unit: string): string {
    if (value === null || value === undefined) {
      return this.isGerman ? 'Keine belastbare Angabe' : 'Not quantified';
    }
    return this.formatNumber(value) + (unit ? ' ' + unit : '');
  }

  formatImprovement(value: number | null): string {
    if (value === null || value === undefined) {
      return this.isGerman ? 'Nicht berechenbar' : 'Not calculable';
    }
    const formatted = new Intl.NumberFormat(this.isGerman ? 'de-DE' : 'en-US', {
      maximumFractionDigits: 2,
      signDisplay: 'always'
    }).format(value);
    return formatted + '%';
  }
}
