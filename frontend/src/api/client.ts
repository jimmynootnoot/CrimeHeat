import axios from 'axios';

// VITE_API_BASE_URL is the current name; VITE_API_URL is accepted as a fallback
// so an existing local .env keeps working after the rename.
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  import.meta.env.VITE_API_URL ??
  (import.meta.env.DEV ? 'http://localhost:8000' : '');

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLoginRequest = error.config?.url?.includes('/api/auth/login');
    if (error.response?.status === 401 && !isLoginRequest) {
      // A 401 on any authenticated request means the token is missing/expired/invalid.
      // Clear the full session (not just the token) and bounce to login — otherwise
      // AuthContext's `user` state stays stale, ProtectedRoute keeps rendering the
      // protected page, and every subsequent call 401s in a way that pages misreport
      // as "backend unreachable" instead of "your session expired."
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_email');
      localStorage.removeItem('user_role');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const DATA_SOURCE = import.meta.env.VITE_DATA_SOURCE ?? 'official';

export const APP_NAME =
  import.meta.env.VITE_APP_NAME ?? 'PPALMA Persistent Crime Pattern Analysis Tool';
