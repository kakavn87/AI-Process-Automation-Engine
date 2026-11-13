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

        if (!result.processSessionId) {
          this.store.setError(language === 'de'
            ? 'Die Analyse wurde abgeschlossen, aber es wurde keine Workflow-Session erstellt. Bitte versuchen Sie es erneut.'
            : 'Analysis completed, but no workflow session was created. Please try again.');
          return;
        }

        void this.router.navigate(['/sessions', result.processSessionId]).then(navigated => {
          if (!navigated) {
            this.store.setError(language === 'de'
              ? 'Die Fragen konnten nicht geöffnet werden. Bitte laden Sie die Seite neu und versuchen Sie es erneut.'
              : 'Could not open the clarification form. Please reload the page and try again.');
          }
        }).catch(() => {
          this.store.setError(language === 'de'
            ? 'Die Fragen konnten nicht geöffnet werden. Bitte laden Sie die Seite neu und versuchen Sie es erneut.'
            : 'Could not open the clarification form. Please reload the page and try again.');
        });
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
