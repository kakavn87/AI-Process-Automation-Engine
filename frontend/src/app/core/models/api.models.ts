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
  cadence: { frequency: string; day: string | null };
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
  confirmedContext?: Array<{ questionId: string; answer: string | boolean }>;
  executionPolicy?: {
    mode: string;
    externalActionsRequireApproval: boolean;
    externalActionsEnabled: boolean;
  };
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
  confirmedDetails?: Array<{ questionId: string; answer: string | boolean }>;
}

export interface OpenQuestion {
  id: string;
  prompt: string;
  type: 'text' | 'boolean' | string;
  required: boolean;
  options: string[];
  placeholder?: string;
  answered?: boolean;
}

export interface ProcessDocumentSource {
  filename: string;
  fileType: string;
  extractedCharacters: number;
  pages: number | null;
  visualAssets: number;
}

export interface ProcessAnalysis {
  automationScore: number;
  automationScoreNote?: string;
  signals: string[];
  description: string;
  sourceDocuments?: ProcessDocumentSource[];
  documentWarnings?: string[];
  knowledgeBase?: { enabled: boolean; indexedChunks: number; status: string; retrievedChunks: number; scope: string };
  sourceEvidence?: Array<{ filename: string; page: number | null; score: number; excerpt: string }>;
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
  humanApproval: { required: boolean; reason: string; gateBefore: string };
  risks: string[];
  assumptions: string[];
  questions: string[];
  proposedWorkflow: ProposedWorkflow;
  processSessionId?: string;
  workflowStatus?: string;
  openQuestions?: OpenQuestion[];
  processingResult?: {
    engine: string;
    status: string;
    preparedAt: string;
    externalActionsExecuted: boolean;
  };
}

export interface WorkflowSessionEvent {
  event: string;
  status: string;
  message: string;
  executionId?: string;
  recordedAt?: string;
}

export interface WorkflowSession {
  id: string;
  description: string;
  analysisStrategy: string;
  language: 'de' | 'en';
  businessDomain: string;
  status: string;
  analysis: ProcessAnalysis;
  answers: Record<string, string | boolean>;
  questions: OpenQuestion[];
  openQuestions: OpenQuestion[];
  relatedExecutionId: string | null;
  events: WorkflowSessionEvent[];
  createdAt: string | null;
  updatedAt: string | null;
}

export interface AIUsageEvent {
  id: string;
  sessionId: string | null;
  provider: string;
  model: string;
  task: string;
  status: string;
  inputTokens: number | null;
  outputTokens: number | null;
  totalTokens: number | null;
  estimatedCostUsd: number | null;
  durationMs: number | null;
  errorType: string | null;
  createdAt: string | null;
}

export interface AIUsageSummary {
  totalCalls: number;
  successfulCalls: number;
  fallbackCalls: number;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  estimatedCostUsd: number | null;
  pricedCalls: number;
  pricingConfigured: boolean;
  events: AIUsageEvent[];
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
  recordedAt?: string;
  externalSideEffect?: boolean;
}

export interface IntegrationReadiness {
  aiGateway: {
    provider: string;
    configured: boolean;
    baseUrlConfigured: boolean;
    model: string;
    visionModel?: string;
    embeddingModel?: string;
    status: string;
  };
  rag: {
    enabled: boolean;
    configured: boolean;
    connected: boolean;
    status: string;
    collection: string;
    embeddingModel: string;
    scope: string;
    message: string;
  };
  openWebUI: { configured: boolean; url: string | null; status: string };
  businessConnectors: Array<{ id: string; name: string; status: string; description: string }>;
  liveWebhook: LiveExecutionReadiness;
  securityNote: string;
}

export interface LiveExecutionReadiness {
  provider: string;
  enabled: boolean;
  ready: boolean;
  endpointConfigured: boolean;
  status: 'ready' | 'disabled' | 'missing_endpoint' | 'invalid_endpoint' | string;
  message: string;
  secretConfigured: boolean;
  operatorTokenConfigured: boolean;
}

export interface ApprovalExecution {
  id: string;
  workflowName: string;
  status: 'awaiting_approval' | 'completed' | 'rejected' | string;
  decisionNote: string | null;
  createdAt: string | null;
  updatedAt: string | null;
  executionMode: 'simulation' | 'live_webhook' | string;
  liveExecutionStatus?: 'not_started' | 'running' | 'succeeded' | 'failed' | 'unknown' | string;
  events: ExecutionEvent[];
}
