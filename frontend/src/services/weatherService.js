import apiClient from './api';

export const weatherService = {
  async getForecast(latitude = 31.0267, longitude = 75.7871, district = 'Jalandhar', includeSimulated = true) {
    const params = {
      latitude,
      longitude,
      district,
      include_simulated: includeSimulated,
    };
    const response = await apiClient.get('/weather/forecast', { params });
    return response.data || response;
  },
};

export default weatherService;

