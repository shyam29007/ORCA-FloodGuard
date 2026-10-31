import apiClient from './api';

export const alertService = {
  async getPendingAlerts() {
    const response = await apiClient.get('/alerts/pending');
    return response.data || response;
  },

  async getAlert(alertId) {
    const response = await apiClient.get(`/alerts/${alertId}`);
    return response.data || response;
  },

  async draftAlert(villageName, overallRisk = 'HIGH', rainfall24h = 65.0, assessmentId = null) {
    const params = {
      village_name: villageName,
      overall_risk: overallRisk,
      rainfall_24h_mm: rainfall24h,
    };
    if (assessmentId) params.assessment_id = assessmentId;
    const response = await apiClient.post('/alerts/draft', null, { params });
    return response.data || response;
  },

  async createAlertDraft(payload) {
    const villageName = payload.village_name;
    const overallRisk = payload.risk_level || payload.overall_risk || 'HIGH';
    const rainfall24h = payload.rainfall_24h_mm || 65.0;
    const assessmentId = payload.assessment_id || payload.assessmentId;
    return this.draftAlert(villageName, overallRisk, rainfall24h, assessmentId);
  },

  async approveAlert(alertId, approvalPayload) {
    const response = await apiClient.post(`/alerts/${alertId}/approve`, approvalPayload);
    return response.data || response;
  },
};

export default alertService;

