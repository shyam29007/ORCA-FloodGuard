import apiClient from './api';

export const replayService = {
  async startReplay(eventName = '2023_punjab_monsoon_floods', targetVillages = ['Gidderpindi', 'Shahkot', 'Phillaur'], stepSizeHours = 6) {
    const payload = {
      event_name: eventName,
      target_villages: targetVillages,
      start_date: '2023-07-09T00:00:00Z',
      end_date: '2023-07-12T00:00:00Z',
      step_size_hours: stepSizeHours,
    };
    const response = await apiClient.post('/replay/start', payload);
    return response.data || response;
  },

  async getReplayStatus(replayId) {
    const response = await apiClient.get(`/replay/${replayId}`);
    return response.data || response;
  },

  async advanceStep(replayId, stepsToAdvance = 1) {
    const response = await apiClient.post(`/replay/${replayId}/step`, { steps_to_advance: stepsToAdvance });
    return response.data || response;
  },
};

export default replayService;

