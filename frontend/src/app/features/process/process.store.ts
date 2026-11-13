import { Injectable, computed, signal } from '@angular/core';
import { ProcessAnalysis } from './process.models';

@Injectable({ providedIn: 'root' })
export class ProcessStore {
  private readonly _description = signal('');
  private readonly _analysis = signal<ProcessAnalysis | null>(null);
  private readonly _loading = signal(false);
  private readonly _error = signal<string | null>(null);

  readonly description = this._description.asReadonly();
  readonly analysis = this._analysis.asReadonly();
  readonly loading = this._loading.asReadonly();
  readonly error = this._error.asReadonly();

  readonly automationScore = computed(
    () => this._analysis()?.automationScore ?? 0
  );

  setDescription(value: string) {
    this._description.set(value);
  }

  setAnalysis(value: ProcessAnalysis) {
    this._analysis.set(value);
  }

  setLoading(value: boolean) {
    this._loading.set(value);
  }

  setError(value: string | null) {
    this._error.set(value);
  }
}
