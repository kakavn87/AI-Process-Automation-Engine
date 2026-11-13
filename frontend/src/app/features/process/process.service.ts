import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { ProcessStore } from './process.store';

@Injectable({ providedIn: 'root' })
export class ProcessService {
  private readonly api = inject(ApiService);
  private readonly store = inject(ProcessStore);
  private readonly router = inject(Router);

  analyze(description: string, analysisStrategy: 'auto' | 'rules' | 'llm' = 'auto', language: 'de' | 'en' = 'de', businessDomain = 'general') {
    this.store.setLoading(true);
    this.store.setError(null);

    this.api.analyzeProcess(description, analysisStrategy, language, businessDomain).subscribe({
      next: result => {
        this.store.setAnalysis(result);
        this.store.setLoading(false);
        if (result.processSessionId) {
          this.router.navigate(['/sessions', result.processSessionId]);
        }
      },
      error: () => {
        this.store.setError(language === 'de'
          ? 'Der Prozess konnte nicht analysiert werden. Bitte prüfen Sie die Backend-Verbindung.'
          : 'Could not analyze the process. Please check the backend connection.');
        this.store.setLoading(false);
      }
    });
  }
}
