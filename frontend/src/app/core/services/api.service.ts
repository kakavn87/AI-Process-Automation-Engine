import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import {
  ExecutionRecord,
  ProcessAnalysis,
  ProposedWorkflow,
} from '../models/api.models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/api`;

  analyzeProcess(description: string) {
    return this.http.post<ProcessAnalysis>(`${this.baseUrl}/processes/analyze`, { description });
  }

  createExecution(workflow: ProposedWorkflow) {
    return this.http.post<ExecutionRecord>(`${this.baseUrl}/executions/`, { workflow });
  }

  approveExecution(id: number, note: string) {
    return this.http.post<ExecutionRecord>(`${this.baseUrl}/executions/${id}/approve`, { note });
  }

  rejectExecution(id: number, note: string) {
    return this.http.post<ExecutionRecord>(`${this.baseUrl}/executions/${id}/reject`, { note });
  }
}
