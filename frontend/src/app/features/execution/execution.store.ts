import { Injectable, signal } from '@angular/core';
import { ExecutionRecord } from '../../core/models/api.models';

@Injectable({ providedIn: 'root' })
export class ExecutionStore {
  private readonly _execution = signal<ExecutionRecord | null>(null);
  private readonly _loading = signal(false);
  private readonly _error = signal<string | null>(null);

  readonly execution = this._execution.asReadonly();
  readonly loading = this._loading.asReadonly();
  readonly error = this._error.asReadonly();

  setExecution(execution: ExecutionRecord | null) {
    this._execution.set(execution);
  }

  setLoading(value: boolean) {
    this._loading.set(value);
  }

  setError(value: string | null) {
    this._error.set(value);
  }
}
