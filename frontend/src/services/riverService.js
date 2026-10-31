import apiClient from './api';

export const riverService = {
  async getStations() {
    const response = await apiClient.get('/river/stations');
    return response.data || response;
  },

  async getReading(stationId) {
    const response = await apiClient.get(`/river/readings/${stationId}`);
    return response.data || response;
  },

  async getStatus(stationId) {
    const response = await apiClient.get(`/river/status/${stationId}`);
    return response.data || response;
  },

  async getAllRiverReadings(stationIds = null, isSimulated = true) {
    try {
      const stations = await this.getStations();
      const stList = Array.isArray(stations) ? stations : [];
      const readings = await Promise.all(
        stList.map(async (st) => {
          try {
            const rd = await this.getReading(st.station_id);
            return {
              ...st,
              reading: rd,
              current_water_level_m: rd?.water_level_meters,
              discharge_cusecs: rd?.discharge_cusecs,
              is_above_warning: rd?.is_above_warning,
              is_above_danger: rd?.is_above_danger,
              trend: rd?.trend,
            };
          } catch {
            return {
              ...st,
              reading: null,
              current_water_level_m: null,
            };
          }
        })
      );
      return readings;
    } catch {
      return [];
    }
  },
};

export default riverService;

