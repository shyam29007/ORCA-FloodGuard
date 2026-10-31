import apiClient from './api';

export const reportService = {
  async getReports(status = null, limit = 50) {
    const params = { limit };
    if (status && status !== 'ALL') params.status_filter = status;
    const response = await apiClient.get('/reports', { params });
    return response.data || response;
  },

  async getReport(reportId) {
    const response = await apiClient.get(`/reports/${reportId}`);
    return response.data || response;
  },

  async uploadReport(payload) {
    const response = await apiClient.post('/reports/upload', payload);
    return response.data || response;
  },

  async reviewReport(reportId, reviewPayload) {
    const response = await apiClient.post(`/reports/${reportId}/review`, reviewPayload);
    return response.data || response;
  },
};

export default reportService;

