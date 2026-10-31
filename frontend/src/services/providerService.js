import apiClient from './api';

export const providerService = {
  async getStatus() {
    return apiClient.get('/providers/status');
  },

  async getHealth(providerName) {
    return apiClient.get(`/providers/${providerName.toLowerCase()}/health`);
  },

  async probeAll() {
    return apiClient.post('/providers/probe');
  },

  async probeProvider(providerName) {
    return apiClient.post(`/providers/${providerName.toLowerCase()}/probe`);
  },
};

export default providerService;

