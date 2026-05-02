export type AgentRole = "ceo" | "manager" | "worker";

export type AgentDefinition = {
  id: string;
  tenantId: string;
  projectId: string;
  role: AgentRole;
  name: string;
  instructions: string;
};
