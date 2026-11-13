export interface WorkflowStepAnalysis {
  id: string;
  type: string;
  name: string;
  description: string;
  config: Record<string, unknown>;
}

export interface ProcessIntegration {
  name: string;
  purpose: string;
  status: string;
}

export interface AutomationOpportunity {
  title: string;
  description: string;
  impact: 'high' | 'medium' | 'low' | string;
}

export interface ProposedWorkflow {
  name: string;
  trigger: string;
  steps: WorkflowStepAnalysis[];
}

export interface ProcessAnalysis {
  automationScore: number;
  signals: string[];
  description: string;
  analysisMode: 'openai_llm' | 'rules_fallback' | string;
  analysisNote: string;
  summary: string;
  currentProcess: string[];
  automationOpportunities: AutomationOpportunity[];
  integrations: ProcessIntegration[];
  humanApproval: {
    required: boolean;
    reason: string;
    gateBefore: string;
  };
  risks: string[];
  assumptions: string[];
  questions: string[];
  proposedWorkflow: ProposedWorkflow;
}

export type ExecutionStatus = 'awaiting_approval' | 'approved_ready' | 'rejected';

export interface ExecutionStepRecord {
  id: string;
  type: string;
  name: string;
  description: string;
  status: string;
  position: number;
}

export interface ExecutionRecord {
  id: number;
  workflowName: string;
  status: ExecutionStatus;
  workflow: ProposedWorkflow;
  decisionNote: string;
  createdAt: string | null;
  decidedAt: string | null;
  steps: ExecutionStepRecord[];
  executionNote: string;
}
