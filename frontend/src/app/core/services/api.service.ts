import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import {
  AIUsageSummary,
  ApprovalExecution,
  ProcessAnalysis,
  ProposedWorkflow,
  TabularDataResult,
  WorkflowSession
} from '../models/api.models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl + '/api';

  analyzeProcess(description: string, analysisStrategy: 'auto' | 'rules' | 'llm' = 'auto', language: 'de' | 'en' = 'de', businessDomain = 'general') {
    return this.http.post<ProcessAnalysis>(this.baseUrl + '/processes/analyze', {
      description,
      analysis_strategy: analysisStrategy,
      analysis_language: language,
      business_domain: businessDomain
    });
  }

  getWorkflowSession(id: string) {
    return this.http.get<WorkflowSession>(
      this.baseUrl + '/processes/sessions/' + encodeURIComponent(id)
    );
  }

  submitWorkflowAnswers(id: string, answers: Record<string, string | boolean>) {
    return this.http.post<WorkflowSession>(
      this.baseUrl + '/processes/sessions/' + encodeURIComponent(id) + '/answers',
      { answers }
    );
  }

  createSessionExecution(id: string) {
    return this.http.post<{ session: WorkflowSession; execution: ApprovalExecution }>(
      this.baseUrl + '/processes/sessions/' + encodeURIComponent(id) + '/execute',
      {}
    );
  }

  getUsageSummary(limit = 25) {
    return this.http.get<AIUsageSummary>(this.baseUrl + '/monitoring/usage?limit=' + limit);
  }

  uploadDataFile(file: File, language: 'de' | 'en' = 'de') {
    const formData = new FormData();
    formData.append('file', file, file.name);
    return this.http.post<TabularDataResult>(this.baseUrl + '/data-processing/upload?language=' + language, formData);
  }

  startExecution(workflow: ProposedWorkflow) {
    return this.http.post<ApprovalExecution>(this.baseUrl + '/executions/', { workflow });
  }

  approveExecution(id: string, note = '') {
    return this.http.post<ApprovalExecution>(
      this.baseUrl + '/executions/' + encodeURIComponent(id) + '/approve',
      { note }
    );
  }

  rejectExecution(id: string, note = '') {
    return this.http.post<ApprovalExecution>(
      this.baseUrl + '/executions/' + encodeURIComponent(id) + '/reject',
      { note }
    );
  }

  getExecution(id: string) {
    return this.http.get<ApprovalExecution>(
      this.baseUrl + '/executions/' + encodeURIComponent(id)
    );
  }
}
