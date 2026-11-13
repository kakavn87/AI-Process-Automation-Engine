export interface ExecutionState {
  status: 'idle' | 'running' | 'awaiting_approval' | 'completed' | 'failed';
}
