import { Injectable, inject } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { ProcessStore } from './process.store';

@Injectable({ providedIn: 'root' })
export class ProcessService {
  private readonly api = inject(ApiService);
  private readonly store = inject(ProcessStore);

  analyze(description: string) {
    this.store.setLoading(true);
    this.store.setError(null);

    this.api.analyzeProcess(description).subscribe({
      next: result => {
        this.store.setAnalysis(result as any);
        this.store.setLoading(false);
      },
      error: () => {
        this.store.setError('Could not analyze process.');
        this.store.setLoading(false);
      }
    });
  }
}
