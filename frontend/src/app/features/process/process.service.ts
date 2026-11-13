import { Injectable, inject } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { ProcessStore } from './process.store';

@Injectable({ providedIn: 'root' })
export class ProcessService {
  private readonly api = inject(ApiService);
  private readonly store = inject(ProcessStore);

  analyze(description: string, analysisStrategy: 'auto' | 'rules' | 'llm' = 'auto') {
    this.store.setLoading(true);
    this.store.setError(null);

    this.api.analyzeProcess(description, analysisStrategy).subscribe({
      next: result => {
        this.store.setAnalysis(result);
        this.store.setLoading(false);
      },
      error: () => {
        this.store.setError('Could not analyze process. Please check that the backend is available and try again.');
        this.store.setLoading(false);
      }
    });
  }
}
