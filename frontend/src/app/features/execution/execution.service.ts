import { Injectable, inject } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { ProposedWorkflow } from '../../core/models/api.models';
import { ExecutionStore } from './execution.store';

@Injectable({ providedIn: 'root' })
export class ExecutionService {
  private readonly api = inject(ApiService);
  private readonly store = inject(ExecutionStore);

  create(workflow: ProposedWorkflow) {
    this.store.setLoading(true);
    this.store.setError(null);
    this.api.startExecution(workflow).subscribe({
      next: result => {
        this.store.setExecution(result);
        this.store.setLoading(false);
      },
      error: error => {
        this.store.setError(error?.error?.detail ?? 'Could not create the approval request.');
        this.store.setLoading(false);
      },
    });
  }

  approve(id: string, note = '') {
    this.store.setLoading(true);
    this.store.setError(null);
    this.api.approveExecution(id, note).subscribe({
      next: result => {
        this.store.setExecution(result);
        this.store.setLoading(false);
      },
      error: error => {
        this.store.setError(error?.error?.detail ?? 'Could not approve this workflow.');
        this.store.setLoading(false);
      },
    });
  }

  reject(id: string, note = '') {
    this.store.setLoading(true);
    this.store.setError(null);
    this.api.rejectExecution(id, note).subscribe({
      next: result => {
        this.store.setExecution(result);
        this.store.setLoading(false);
      },
      error: error => {
        this.store.setError(error?.error?.detail ?? 'Could not reject this workflow.');
        this.store.setLoading(false);
      },
    });
  }
}
