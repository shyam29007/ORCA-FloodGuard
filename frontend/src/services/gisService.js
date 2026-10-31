import apiClient from './api';

export const gisService = {
  async getLocationInfo(latitude, longitude, villageName = null) {
    const params = { latitude, longitude };
    if (villageName) params.village_name = villageName;
    const response = await apiClient.get('/gis/location', { params });
    return response.data || response;
  },
};

export default gisService;

