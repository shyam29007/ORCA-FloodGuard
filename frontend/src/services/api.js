import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

// Request interceptor: attach bearer token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('orca_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle errors & normalize responses
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    let message = 'An unexpected network error occurred.';
    let details = null;

    if (error.response) {
      const data = error.response.data;
      message = data?.detail || data?.message || `Server error (${error.response.status})`;
      details = data?.details || null;

      // Handle token expiration and unauthorized rejection
      if (error.response.status === 401 && !error.config.url.includes('/auth/login')) {
        localStorage.removeItem('orca_token');
        localStorage.removeItem('orca_user');
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new Event('orca-auth-expired'));
        }
      }
    } else if (error.request) {
      message = 'Could not establish connection to ORCA-FloodGuard backend. Verify backend is running on port 8000.';
    }

    const enhancedError = new Error(message);
    enhancedError.status = error.response?.status;
    enhancedError.details = details;
    return Promise.reject(enhancedError);
  }
);

export default apiClient;

