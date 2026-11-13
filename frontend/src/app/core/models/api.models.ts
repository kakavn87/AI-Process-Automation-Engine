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

export interface DetectedProcessDetails {
  businessDomain: string;
  businessDomainLabel?: string;
  cadence: {
    frequency: string;
    day: string | null;
  };
  sourceChannels: string[];
  fileTypes: string[];
  activities: string[];
  activityLabels: string[];
  deliveryChannels: string[];
  systems: string[];
  outputTypes: string[];
  roles: string[];
  extractionMethod: string;
}

export interface ProposedWorkflow {
  name: string;
  trigger: string;
  steps: WorkflowStepAnalysis[];
}

export interface RoutingDecision {
  requestedStrategy: 'auto' | 'rules' | 'llm';
  selectedEngine: 'rules' | 'llm';
  llmAvailable: boolean;
  ruleConfidence: number;
  rulesSuitable: boolean;
  complexityFlags: string[];
  reason: string;
}

export interface ProcessSpecification {
  schemaVersion: string;
  businessDomain: string;
  businessDomainLabel: string;
  goal: string;
  actors: string[];
  inputs: string[];
  systems: string[];
  businessRules: string[];
  exceptionPaths: string[];
  outputs: string[];
  successMetrics: string[];
}

export interface ProcessAnalysis {
  automationScore: number;
  signals: string[];
  description: string;
  analysisMode: string;
  analysisNote: string;
  llmUsed: boolean;
  llmModel: string | null;
  detectedDetails: DetectedProcessDetails;
  processSpecification?: ProcessSpecification;
  routingDecision: RoutingDecision;
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

export interface TabularDataColumn {
  name: string;
  detectedType: string;
  missingCount: number;
  missingPercent: number;
  uniqueCount: number;
  sampleValues: Array<string | number | boolean>;
  numericSummary: { min: number; max: number; mean: number } | null;
}

export interface TabularDataResult {
  fileName: string;
  fileType: string;
  sheetName: string | null;
  totalRows: number;
  processedRows: number;
  totalColumns: number;
  duplicateRows: number;
  emptyRowsRemoved: number;
  truncated: boolean;
  dataQualityScore: number;
  columns: TabularDataColumn[];
  preview: Array<Record<string, string | number | boolean | null>>;
  processingSteps: string[];
  notice: string;
}

export interface ExecutionEvent {
  event?: string;
  stepId?: string;
  step?: string;
  status: string;
  message: string;
}

export interface ApprovalExecution {
  id: string;
  workflowName: string;
  status: 'awaiting_approval' | 'completed' | 'rejected' | string;
  decisionNote: string | null;
  createdAt: string | null;
  updatedAt: string | null;
  executionMode: 'simulation' | string;
  events: ExecutionEvent[];
}
