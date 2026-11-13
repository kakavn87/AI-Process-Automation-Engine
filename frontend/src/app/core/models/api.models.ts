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
  analysisMode: string;
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
