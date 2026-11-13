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
    this.api.createExecution(workflow).subscribe({
      next: result => {
        this.store.setExecution(result);
        this.store.setLoading(false);
      },
      error: () => {
        this.store.setError('Could not create the approval request. Please try again.');
        this.store.setLoading(false);
      },
    });
  }

  approve(id: number, note = '') {
    this.store.setLoading(true);
    this.store.setError(null);
    this.api.approveExecution(id, note).subscribe({
      next: result => {
        this.store.setExecution(result);
        this.store.setLoading(false);
      },
      error: () => {
        this.store.setError('Could not approve this workflow. It may already have a decision.');
        this.store.setLoading(false);
      },
    });
  }

  reject(id: number, reason: string) {
    this.store.setLoading(true);
    this.store.setError(null);
    this.api.rejectExecution(id, reason).subscribe({
      next: result => {
        this.store.setExecution(result);
        this.store.setLoading(false);
      },
      error: () => {
        this.store.setError('Could not reject this workflow. Check the rejection reason and try again.');
        this.store.setLoading(false);
      },
    });
  }
}
