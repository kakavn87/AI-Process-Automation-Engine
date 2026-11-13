import { Injectable, signal } from '@angular/core';
import { ExecutionState } from './execution.models';

@Injectable({ providedIn: 'root' })
export class ExecutionStore {
  private readonly _state = signal<ExecutionState>({ status: 'idle' });
  readonly state = this._state.asReadonly();

  setState(state: ExecutionState) {
    this._state.set(state);
  }
}
