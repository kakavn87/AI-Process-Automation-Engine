import { Injectable, signal } from '@angular/core';
import { WorkflowStep } from './workflow.models';

@Injectable({ providedIn: 'root' })
export class WorkflowStore {
  private readonly _steps = signal<WorkflowStep[]>([]);
  readonly steps = this._steps.asReadonly();

  setSteps(steps: WorkflowStep[]) {
    this._steps.set(steps);
  }
}
