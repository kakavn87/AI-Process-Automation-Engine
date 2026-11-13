export type { ApprovalExecution, ExecutionEvent } from '../../core/models/api.models';

export interface ExecutionState {
  status: 'idle' | 'loading' | 'awaiting_approval' | 'completed' | 'rejected' | 'failed';
}
