import apiClient from './api';

export const authService = {
  async login(email, password) {
    const data = await apiClient.post('/auth/login', { email, password });
    if (data.access_token) {
      localStorage.setItem('orca_token', data.access_token);
      localStorage.setItem('orca_user', JSON.stringify(data.user));
    }
    return data;
  },

  async register(registrationData) {
    const data = await apiClient.post('/auth/register', registrationData);
    if (data.access_token) {
      localStorage.setItem('orca_token', data.access_token);
      localStorage.setItem('orca_user', JSON.stringify(data.user));
    }
    return data;
  },

  async getMe() {
    return apiClient.get('/auth/me');
  },

  async getDemoAccounts() {
    return apiClient.get('/auth/demo-accounts');
  },

  logout() {
    localStorage.removeItem('orca_token');
    localStorage.removeItem('orca_user');
  },

  getCurrentUser() {
    try {
      const userStr = localStorage.getItem('orca_user');
      return userStr ? JSON.parse(userStr) : null;
    } catch {
      return null;
    }
  },
};

export default authService;

