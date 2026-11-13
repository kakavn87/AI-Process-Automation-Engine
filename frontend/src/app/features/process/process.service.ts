import { Injectable, inject } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { ProcessStore } from './process.store';

@Injectable({ providedIn: 'root' })
export class ProcessService {
  private readonly api = inject(ApiService);
  private readonly store = inject(ProcessStore);

  analyze(
    description: string,
    analysisStrategy: 'auto' | 'rules' | 'llm' = 'auto',
    language: 'de' | 'en' = 'de',
    businessDomain = 'general',
    files: File[] = [],
    documentIds: string[] = []
  ): void {
    this.store.setLoading(true);
    this.store.setError(null);

    const request = files.length
      ? this.api.analyzeProcessWithDocuments(description, files, analysisStrategy, language, businessDomain, documentIds)
      : this.api.analyzeProcess(description, analysisStrategy, language, businessDomain, documentIds);

    request.subscribe({
      next: result => {
        this.store.setAnalysis(result);
        this.store.setLoading(false);

        if (!result.processSessionId) {
          this.store.setError(language === 'de'
            ? 'Die Analyse wurde abgeschlossen, aber es wurde keine Workflow-Session erstellt. Bitte versuchen Sie es erneut.'
            : 'Analysis completed, but no workflow session was created. Please try again.');
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
