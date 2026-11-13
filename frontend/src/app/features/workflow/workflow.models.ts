export interface WorkflowStep {
  type: string;
  name: string;
  config: Record<string, unknown>;
}
