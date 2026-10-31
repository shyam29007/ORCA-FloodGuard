import apiClient from './api';

export const damService = {
  async getDamInformation(riverBasin = null, includeSimulated = true) {
    const params = {
      include_simulated: includeSimulated,
    };
    if (riverBasin) params.river_basin = riverBasin;
    const response = await apiClient.get('/dam/information', { params });
    return response.data || response;
  },
};

export default damService;

