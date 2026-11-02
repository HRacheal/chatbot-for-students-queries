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

// Endpoints that require the staff token (all dashboard roles; the backend checks each role).
const ADMIN_PATHS = ['/api/admin/', '/api/staff/', '/api/pdfs', '/api/unanswered-queries', '/api/add-response', '/api/delete-query'];
const LOGIN_PATHS = ['/api/admin/login', '/api/staff/login'];
const isAdminPath = (url = '') => ADMIN_PATHS.some((path) => url.startsWith(path)) && !LOGIN_PATHS.includes(url);

// The staff session: a bearer token (expires on the server) plus the profile returned at sign-in,
// used only to decide what to show. Every permission is enforced again by the backend.
export const STAFF_PROFILE_KEY = 'staffProfile';
export const getStaffProfile = () => {
  try {
    return JSON.parse(localStorage.getItem(STAFF_PROFILE_KEY) || 'null');
  } catch {
    return null;
  }
};
export const saveStaffSession = (token, profile) => {
  if (token) localStorage.setItem('adminToken', token);
  if (profile) localStorage.setItem(STAFF_PROFILE_KEY, JSON.stringify(profile));
};
export const clearStaffSession = () => {
  localStorage.removeItem('adminToken');
  localStorage.removeItem(STAFF_PROFILE_KEY);
};

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
      clearStaffSession();
      if (window.location.pathname.startsWith('/admin/')) {
        window.location.href = '/admin';
      }
    }
    if (error.response?.data?.code === 'password_change_required' && window.location.pathname.startsWith('/admin/')) {
      window.location.href = '/admin?change-password=1';
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

// Message shown in the chat when a question could not be processed. It never contains an
// answer, and says whether the problem is the connection, the server or the request.
export const chatErrorMessage = (error) => {
  const response = error?.response;
  if (!response) {
    return 'Could not reach the USIUBOT server. Please check your connection and try again.';
  }
  const message = typeof response.data?.error === 'string' ? response.data.error : '';
  if (response.status === 429) return message || 'Too many questions in a short time. Please wait a minute and try again.';
  if (response.status >= 400 && response.status < 500) return message || 'This question could not be sent. Please rephrase it and try again.';
  if (message) return message;
  return 'The USIUBOT server could not answer right now, so no answer was given. Please try again later.';
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

// Approved knowledge sources (admin)
export const fetchSources = async (params = {}) => (await api.get('/api/admin/sources', { params })).data;
export const getSource = async (id) => (await api.get(`/api/admin/sources/${encodeURIComponent(id)}`)).data;
export const createSource = async (data) => {
  if (data instanceof FormData) {
    return (await api.post('/api/admin/sources', data, { headers: { 'Content-Type': 'multipart/form-data' } })).data;
  }
  return (await api.post('/api/admin/sources', data)).data;
};
export const updateSource = async (id, data) =>
  (await api.put(`/api/admin/sources/${encodeURIComponent(id)}`, data)).data;
export const setSourceStatus = async (id, status, note = '') =>
  (await api.post(`/api/admin/sources/${encodeURIComponent(id)}/status`, { status, note })).data;
export const rebuildSourceIndex = async () => (await api.post('/api/admin/sources/rebuild-index')).data;
export const bulkSetSourceStatus = async (ids, status, note = '') =>
  (await api.post('/api/admin/sources/bulk-status', { ids, status, note })).data;

// USIUBOT dataset import (creates draft sources only) and retrieval test (admin)
export const getDatasetStatus = async () => (await api.get('/api/admin/dataset/status')).data;
export const importDataset = async (dryRun) => (await api.post('/api/admin/dataset/import', { dry_run: dryRun })).data;
export const searchDataset = async (q, category = '') =>
  (await api.get('/api/admin/dataset/search', { params: category ? { q, category } : { q } })).data;

// Department routing (admin)
export const fetchRouting = async () => (await api.get('/api/admin/routing')).data;
export const updateRouting = async (department, data) =>
  (await api.put(`/api/admin/routing/${encodeURIComponent(department)}`, data)).data;
export const importRoutingContacts = async () => (await api.post('/api/admin/routing/import-contacts')).data;

// Official fallback links (admin)
export const fetchOfficialLinks = async () => (await api.get('/api/admin/official-links')).data;
export const saveOfficialLink = async (data) => (await api.post('/api/admin/official-links', data)).data;
export const previewOfficialLinks = async (q) =>
  (await api.get('/api/admin/official-links/preview', { params: { q } })).data;

// Unresolved enquiries (anonymous or logged-in user)
export const getEnquiryOptions = async () => (await api.get('/api/enquiries/options')).data;
export const submitEnquiry = async (data, token) =>
  (await api.post('/api/enquiries', data, { headers: userAuthHeader(token) })).data;
export const trackEnquiry = async (reference, trackingKey) =>
  (await api.post('/api/enquiries/track', { reference, tracking_key: trackingKey })).data;
export const getMyEnquiries = async (token) =>
  (await api.get('/api/my-enquiries', { headers: userAuthHeader(token) })).data;

// Degree guidance. Uploaded files are processed in memory by the backend and not stored.
export const getGuidanceOptions = async () => (await api.get('/api/guidance/options')).data;
export const extractResults = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return (await api.post('/api/guidance/extract', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })).data;
};
export const getRecommendations = async (data) => (await api.post('/api/guidance/recommend', data)).data;

// Enquiry management, programme requirements and live-retrieval status (admin)
export const fetchEnquiries = async (params = {}) => (await api.get('/api/admin/enquiries', { params })).data;
export const getEnquiry = async (id) => (await api.get(`/api/admin/enquiries/${encodeURIComponent(id)}`)).data;
export const updateEnquiryStatus = async (id, data) =>
  (await api.post(`/api/admin/enquiries/${encodeURIComponent(id)}/status`, data)).data;
export const fetchProgrammeRequirements = async () => (await api.get('/api/admin/programme-requirements')).data;
export const createProgrammeRequirement = async (data) =>
  (await api.post('/api/admin/programme-requirements', data)).data;
export const updateProgrammeRequirement = async (id, data) =>
  (await api.put(`/api/admin/programme-requirements/${encodeURIComponent(id)}`, data)).data;
export const deleteProgrammeRequirement = async (id) =>
  (await api.delete(`/api/admin/programme-requirements/${encodeURIComponent(id)}`)).data;
export const getLiveRetrievalStatus = async () => (await api.get('/api/admin/live-retrieval')).data;

// Staff dashboard (role- and department-scoped by the backend)
export const staffLogin = async (credentials) => (await api.post('/api/staff/login', credentials)).data;
export const staffLogout = async () => (await api.post('/api/staff/logout')).data;
export const getStaffMe = async () => (await api.get('/api/staff/me')).data;
export const changeStaffPassword = async (data) => (await api.post('/api/staff/password', data)).data;
export const getStaffOptions = async () => (await api.get('/api/staff/options')).data;
export const fetchStaffAccounts = async (params = {}) => (await api.get('/api/staff/accounts', { params })).data;
export const createStaffAccount = async (data) => (await api.post('/api/staff/accounts', data)).data;
export const updateStaffAccount = async (id, data) =>
  (await api.put(`/api/staff/accounts/${encodeURIComponent(id)}`, data)).data;
export const resetStaffPassword = async (id) =>
  (await api.post(`/api/staff/accounts/${encodeURIComponent(id)}/reset-password`)).data;
export const fetchStaffDirectory = async (department) =>
  (await api.get('/api/staff/directory', { params: department ? { department } : {} })).data;
export const fetchAuditLog = async (params = {}) => (await api.get('/api/staff/audit', { params })).data;
export const getDashboard = async (days = 30) => (await api.get('/api/admin/dashboard', { params: { days } })).data;
export const addEnquiryNote = async (id, text) =>
  (await api.post(`/api/admin/enquiries/${encodeURIComponent(id)}/notes`, { text })).data;

// Auth endpoints
export const adminLogin = async (credentials) => (await api.post('/api/admin/login', credentials)).data;
export const userLogin = async (credentials) => (await api.post('/api/login', credentials)).data;
export const userSignup = async (userData) => (await api.post('/api/signup', userData)).data;
