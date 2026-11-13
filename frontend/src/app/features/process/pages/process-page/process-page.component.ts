import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ProcessStore } from '../../process.store';
import { ProcessService } from '../../process.service';
import { ExecutionStore } from '../../../execution/execution.store';
import { ExecutionService } from '../../../execution/execution.service';

@Component({
  selector: 'app-process-page',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './process-page.component.html'
})
export class ProcessPageComponent {
  readonly store = inject(ProcessStore);
  readonly executionStore = inject(ExecutionStore);
  private readonly service = inject(ProcessService);
  private readonly executionService = inject(ExecutionService);

  description = '';
  approvalNote = '';
  rejectionReason = '';

  analyze() {
    this.store.setDescription(this.description);
    this.executionStore.setExecution(null);
    this.executionStore.setError(null);
    this.service.analyze(this.description);
  }

  createApprovalRequest() {
    const analysis = this.store.analysis();
    if (analysis) {
      this.executionService.create(analysis.proposedWorkflow);
    }
  }

  approveExecution() {
    const execution = this.executionStore.execution();
    if (execution) {
      this.executionService.approve(execution.id, this.approvalNote);
    }
  }

  rejectExecution() {
    const execution = this.executionStore.execution();
    if (execution && this.rejectionReason.trim()) {
      this.executionService.reject(execution.id, this.rejectionReason.trim());
    }
  }
}
