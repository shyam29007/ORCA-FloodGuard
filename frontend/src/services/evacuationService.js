import apiClient from './api';

export const evacuationService = {
  async getRoutes(params = {}) {
    const response = await apiClient.get('/evacuation/routes', { params });
    return response.data || response;
  },

  async getReliefCentres(district = null) {
    const params = district && district !== 'All Districts' ? { district } : {};
    const response = await apiClient.get('/evacuation/relief-centres', { params });
    return response.data || response;
  },
};

export default evacuationService;

