import apiClient from './api';

export const agentService = {
  async getRunStatus(runId) {
    const response = await apiClient.get(`/agents/status/${runId}`);
    return response.data || response;
  },

  async getRunTrace(runId) {
    const response = await apiClient.get(`/agents/trace/${runId}`);
    return response.data || response;
  },
};

export default agentService;

