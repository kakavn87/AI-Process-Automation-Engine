import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { ApprovalExecution, ProcessAnalysis, ProposedWorkflow } from '../models/api.models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/api`;

  analyzeProcess(description: string) {
    return this.http.post<ProcessAnalysis>(`${this.baseUrl}/processes/analyze`, { description });
  }

  startExecution(workflow: ProposedWorkflow) {
    return this.http.post<ApprovalExecution>(`${this.baseUrl}/executions/`, { workflow });
  }

  approveExecution(id: string, note = '') {
    return this.http.post<ApprovalExecution>(
      `${this.baseUrl}/executions/${encodeURIComponent(id)}/approve`,
      { note }
    );
  }

  rejectExecution(id: string, note = '') {
    return this.http.post<ApprovalExecution>(
      `${this.baseUrl}/executions/${encodeURIComponent(id)}/reject`,
      { note }
    );
  }

  getExecution(id: string) {
    return this.http.get<ApprovalExecution>(
      `${this.baseUrl}/executions/${encodeURIComponent(id)}`
    );
  }
}
