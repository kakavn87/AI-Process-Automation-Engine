import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  AIUsageSummary,
  ApprovalExecution,
  IntegrationReadiness,
  LiveExecutionReadiness,
  ProcessAnalysis,
  ProposedWorkflow,
  TabularDataResult,
  WorkflowSession
} from '../models/api.models';

declare global {
  interface Window {
    __FLOWPILOT_RUNTIME_CONFIG__?: {
      apiBaseUrl?: string;
      isPreview?: boolean;
    };
  }
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = (
    window.__FLOWPILOT_RUNTIME_CONFIG__?.apiBaseUrl ?? environment.apiBaseUrl
  ).trim().replace(/\/+$/, '');

  private request<T>(path: string, send: (url: string) => Observable<T>): Observable<T> {
    if (!this.baseUrl) {
      return throwError(() => new Error(
        'The Preview API is not configured. Check that the matching Backend Preview for this pull request is available.'
      ));
    }

    return send(this.baseUrl + '/api' + path);
  }

  analyzeProcess(
    description: string,
    analysisStrategy: 'auto' | 'rules' | 'llm' = 'auto',
    language: 'de' | 'en' = 'de',
    businessDomain = 'general'
  ) {
    return this.request('/processes/analyze', url => this.http.post<ProcessAnalysis>(url, {
      description,
      analysis_strategy: analysisStrategy,
      analysis_language: language,
      business_domain: businessDomain
    }));
  }

  analyzeProcessWithDocuments(
    description: string,
    files: File[],
    analysisStrategy: 'auto' | 'rules' | 'llm' = 'auto',
    language: 'de' | 'en' = 'de',
    businessDomain = 'general'
  ) {
    const formData = new FormData();
    if (description.trim()) formData.append('description', description.trim());
    formData.append('analysis_strategy', analysisStrategy);
    formData.append('analysis_language', language);
    formData.append('business_domain', businessDomain);
    files.forEach(file => formData.append('files', file, file.name));
    return this.request('/processes/analyze-with-documents', url =>
      this.http.post<ProcessAnalysis>(url, formData)
    );
  }

  getWorkflowSession(id: string) {
    return this.request('/processes/sessions/' + encodeURIComponent(id), url =>
      this.http.get<WorkflowSession>(url)
    );
  }

  submitWorkflowAnswers(id: string, answers: Record<string, string | boolean>) {
    return this.request('/processes/sessions/' + encodeURIComponent(id) + '/answers', url =>
      this.http.post<WorkflowSession>(url, { answers })
    );
  }

  createSessionExecution(id: string) {
    return this.request('/processes/sessions/' + encodeURIComponent(id) + '/execute', url =>
      this.http.post<{ session: WorkflowSession; execution: ApprovalExecution }>(url, {})
    );
  }

  getUsageSummary(limit = 25) {
    return this.request('/monitoring/usage?limit=' + limit, url =>
      this.http.get<AIUsageSummary>(url)
    );
  }

  uploadDataFile(file: File, language: 'de' | 'en' = 'de') {
    const formData = new FormData();
    formData.append('file', file, file.name);
    return this.request('/data-processing/upload?language=' + language, url =>
      this.http.post<TabularDataResult>(url, formData)
    );
  }

  startExecution(workflow: ProposedWorkflow) {
    return this.request('/executions/', url =>
      this.http.post<ApprovalExecution>(url, { workflow })
    );
  }

  approveExecution(id: string, note = '') {
    return this.request('/executions/' + encodeURIComponent(id) + '/approve', url =>
      this.http.post<ApprovalExecution>(url, { note })
    );
  }

  rejectExecution(id: string, note = '') {
    return this.request('/executions/' + encodeURIComponent(id) + '/reject', url =>
      this.http.post<ApprovalExecution>(url, { note })
    );
  }

  getIntegrationReadiness() {
    return this.request('/integrations/readiness', url =>
      this.http.get<IntegrationReadiness>(url)
    );
  }

  getLiveExecutionReadiness() {
    return this.request('/executions/live-readiness', url =>
      this.http.get<LiveExecutionReadiness>(url)
    );
  }

  runLiveExecution(id: string, confirmationToken: string) {
    return this.request('/executions/' + encodeURIComponent(id) + '/live', url =>
      this.http.post<ApprovalExecution>(url, {
        confirm_live_execution: true,
        confirmation_token: confirmationToken
      })
    );
  }

  getExecution(id: string) {
    return this.request('/executions/' + encodeURIComponent(id), url =>
      this.http.get<ApprovalExecution>(url)
    );
  }
}
