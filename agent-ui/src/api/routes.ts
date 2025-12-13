export const APIRoutes = {
  GetAgents: (agentOSUrl: string) => `${agentOSUrl}/v1/agents`,
  AgentRun: (agentOSUrl: string) => `${agentOSUrl}/v1/agents/{agent_id}/runs`,
  Status: (agentOSUrl: string) => `${agentOSUrl}/v1/health`,
  GetSessions: (agentOSUrl: string) => `${agentOSUrl}/v1/sessions`,
  GetSession: (agentOSUrl: string, sessionId: string) =>
    `${agentOSUrl}/v1/sessions/${sessionId}/runs`,

  DeleteSession: (agentOSUrl: string, sessionId: string) =>
    `${agentOSUrl}/v1/sessions/${sessionId}`,

  GetTeams: (agentOSUrl: string) => `${agentOSUrl}/v1/teams`,
  TeamRun: (agentOSUrl: string, teamId: string) =>
    `${agentOSUrl}/v1/teams/${teamId}/runs`,
  DeleteTeamSession: (agentOSUrl: string, teamId: string, sessionId: string) =>
    `${agentOSUrl}/v1/teams/${teamId}/sessions/${sessionId}`,

  // Templates
  GetTemplates: (agentOSUrl: string) => `${agentOSUrl}/v1/templates`,
  GetTemplate: (agentOSUrl: string, templateId: string) =>
    `${agentOSUrl}/v1/templates/${templateId}`,

  // Animations
  GenerateAnimation: (agentOSUrl: string) =>
    `${agentOSUrl}/v1/animations/generate`,

  // Datasets
  UploadDataset: (agentOSUrl: string) => `${agentOSUrl}/v1/datasets/upload`,
  GetDatasets: (agentOSUrl: string) => `${agentOSUrl}/v1/datasets`,
  GetDataset: (agentOSUrl: string, datasetId: string) =>
    `${agentOSUrl}/v1/datasets/${datasetId}`
}
