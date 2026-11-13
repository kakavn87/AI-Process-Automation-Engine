import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import {
  AIUsageSummary,
  ApprovalExecution,
  WorkflowSession
} from '../../core/models/api.models';

@Component({
  selector: 'app-workflow-session-page',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './workflow-session-page.component.html',
  styleUrl: './workflow-session-page.component.scss'
})
export class WorkflowSessionPageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(ApiService);

  readonly session = signal<WorkflowSession | null>(null);
  readonly execution = signal<ApprovalExecution | null>(null);
  readonly usage = signal<AIUsageSummary | null>(null);
  readonly answerValues = signal<Record<string, string | boolean>>({});
  readonly loading = signal(false);
  readonly submitting = signal(false);
  readonly executionLoading = signal(false);
  readonly error = signal<string | null>(null);

  private sessionId = '';

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      this.sessionId = params.get('sessionId') ?? '';
      if (this.sessionId) this.loadSession();
    });
    this.loadUsage();
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
    this.api.getWorkflowSession(this.sessionId).subscribe({
      next: result => {
        this.session.set(result);
        this.loading.set(false);
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
    this.api.submitWorkflowAnswers(current.id, submitted).subscribe({
      next: result => {
        this.session.set(result);
        this.answerValues.set({});
        this.submitting.set(false);
      },
      error: error => {
        this.error.set(error?.error?.detail || (this.isGerman
          ? 'Die Antworten konnten nicht gespeichert werden.'
          : 'Could not save the answers.'));
        this.submitting.set(false);
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
}
