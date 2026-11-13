import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';
import { ApprovalExecution } from '../../../../core/models/api.models';
import { ProcessStore } from '../../process.store';
import { ProcessService } from '../../process.service';

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

  readonly execution = signal<ApprovalExecution | null>(null);
  readonly executionLoading = signal(false);
  readonly executionError = signal<string | null>(null);

  description = '';
  analysisStrategy: 'auto' | 'rules' | 'llm' = 'auto';

  analyze() {
    this.execution.set(null);
    this.executionError.set(null);
    this.store.setDescription(this.description);
    this.service.analyze(this.description, this.analysisStrategy);
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
        this.executionError.set(error?.error?.detail ?? 'Could not create the approval request.');
        this.executionLoading.set(false);
      }
    });
  }

  approveExecution() {
    const current = this.execution();
    if (!current || current.status !== 'awaiting_approval' || this.executionLoading()) return;

    this.executionLoading.set(true);
    this.executionError.set(null);
    this.api.approveExecution(current.id, 'Approved from the process dashboard.').subscribe({
      next: result => {
        this.execution.set(result);
        this.executionLoading.set(false);
      },
      error: error => {
        this.executionError.set(error?.error?.detail ?? 'Could not approve this execution.');
        this.executionLoading.set(false);
      }
    });
  }

  rejectExecution() {
    const current = this.execution();
    if (!current || current.status !== 'awaiting_approval' || this.executionLoading()) return;

    this.executionLoading.set(true);
    this.executionError.set(null);
    this.api.rejectExecution(current.id, 'Rejected from the process dashboard.').subscribe({
      next: result => {
        this.execution.set(result);
        this.executionLoading.set(false);
      },
      error: error => {
        this.executionError.set(error?.error?.detail ?? 'Could not reject this execution.');
        this.executionLoading.set(false);
      }
    });
  }
}
