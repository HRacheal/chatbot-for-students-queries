import axios from 'axios';

// Base URL of the backend. Empty in development, where Vite proxies /api.
const baseURL = import.meta.env.VITE_API_BASE_URL || '';

// Authentication uses bearer tokens in the Authorization header (not cookies),
// so requests are sent without credentials.
const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 2 minutes for AI processing
});

// Endpoints that require the administrator token.
const ADMIN_PATHS = ['/api/admin/', '/api/pdfs', '/api/unanswered-queries', '/api/add-response', '/api/delete-query'];
const isAdminPath = (url = '') => ADMIN_PATHS.some((path) => url.startsWith(path)) && url !== '/api/admin/login';

// Attach the admin token to admin endpoints only, unless a header was set explicitly.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('adminToken');
  if (token && isAdminPath(config.url) && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// An expired or invalid admin token sends the administrator back to the login page.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && isAdminPath(error.config?.url)) {
      localStorage.removeItem('adminToken');
      if (window.location.pathname.startsWith('/admin/')) {
        window.location.href = '/admin';
      }
    }
    return Promise.reject(error);
  }
);

export { api };

// Extract a user-friendly message from an API error.
export const getErrorMessage = (error, fallback = 'Something went wrong. Please try again.') => {
  if (!error?.response) return 'Network error. Please check your connection and try again.';
  return error.response.data?.error || fallback;
};

export const getAuthToken = () => localStorage.getItem('adminToken');

const userAuthHeader = (token) => (token ? { Authorization: `Bearer ${token}` } : {});

// PDF Management endpoints (admin)
export const fetchPDFs = async () => (await api.get('/api/pdfs/')).data;

export const uploadPDF = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/api/pdfs/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const deletePDF = async (publicId) =>
  (await api.delete(`/api/pdfs/${publicId.split('/').map(encodeURIComponent).join('/')}`)).data;

export const rebuildEmbeddings = async () =>
  (await api.post('/api/pdfs/rebuild-embeddings', {}, { timeout: 600000 })).data;

// Chat endpoints (anonymous or logged-in user)
export const getChatHistory = async (token) =>
  (await api.get('/api/chat-history', { headers: userAuthHeader(token) })).data;

export const submitQuery = async (query, token) =>
  (await api.post('/api/query', query, { headers: userAuthHeader(token) })).data;

// Admin endpoints
export const getUnansweredQueries = async () => (await api.get('/api/unanswered-queries')).data;
export const getAdminStats = async () => (await api.get('/api/admin/stats')).data;
export const getAdminChatHistory = async () => (await api.get('/api/admin/chat-history')).data;
export const addResponse = async (data) => (await api.post('/api/add-response', data)).data;
export const deleteQuery = async (id) => (await api.delete(`/api/delete-query/${id}`)).data;
export const getQueryAnalytics = async () => (await api.get('/api/admin/query-analytics')).data;

// Auth endpoints
export const adminLogin = async (credentials) => (await api.post('/api/admin/login', credentials)).data;
export const userLogin = async (credentials) => (await api.post('/api/login', credentials)).data;
export const userSignup = async (userData) => (await api.post('/api/signup', userData)).data;
