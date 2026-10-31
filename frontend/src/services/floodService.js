import apiClient from './api';

export const floodService = {
  async assessFloodRisk(payload) {
    const response = await apiClient.post('/flood/assess', payload);
    return response.data || response;
  },

  async getAssessment(assessmentId) {
    const response = await apiClient.get(`/flood/assessments/${assessmentId}`);
    return response.data || response;
  },

  async getVillageOutlook(villageId) {
    const response = await apiClient.get(`/flood/villages/${villageId}/outlook`);
    return response.data || response;
  },
};

export default floodService;

