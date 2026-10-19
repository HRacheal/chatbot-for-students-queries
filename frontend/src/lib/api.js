import axios from 'axios';

// Create axios instance with base URL from environment variable
const baseURL = import.meta.env.VITE_API_BASE_URL || '';
console.log('API Service initialized with baseURL:', baseURL);

const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Important for CORS with credentials
  timeout: 600000, // 10 minutes timeout for AI processing
});

// Add request interceptor to include token with every request
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('adminToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    console.error('Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor to handle errors
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Log detailed error information
    console.error('API Error:', {
      message: error.message,
      endpoint: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      data: error.response?.data,
    });
    
    return Promise.reject(error);
  }
);

// Export the configured axios instance for direct use in components
export { api };

// Get auth token from localStorage
export const getAuthToken = () => {
  const token = localStorage.getItem('adminToken');
  console.log('Auth token retrieved:', token ? 'Token exists' : 'No token found');
  return token;
};

// PDF Management endpoints
export const fetchPDFs = async () => {
  const token = getAuthToken();
  try {
    console.log('Fetching PDFs with token:', token ? 'Token exists' : 'No token found');
    const response = await api.get('/api/pdfs/', {
      headers: { Authorization: `Bearer ${token}` },
    });
    console.log('PDFs fetch successful:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error fetching PDFs:', error);
    throw error;
  }
};

export const uploadPDF = async (file) => {
  const token = getAuthToken();
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    const response = await api.post('/api/pdfs/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error uploading PDF:', error);
    throw error;
  }
};

export const deletePDF = async (publicId) => {
  const token = getAuthToken();
  try {
    const response = await api.delete(`/api/pdfs/${encodeURIComponent(publicId)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    console.error('Error deleting PDF:', error);
    throw error;
  }
};

export const rebuildEmbeddings = async () => {
  const token = getAuthToken();
  try {
    const response = await api.post('/api/pdfs/rebuild-embeddings', {}, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    console.error('Error rebuilding embeddings:', error);
    throw error;
  }
};

// Chat endpoints
export const getChatHistory = async (token) => {
  try {
    const response = await api.get('/api/chat-history', {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching chat history:', error);
    throw error;
  }
};

export const submitQuery = async (query, token) => {
  try {
    const response = await api.post('/api/query', query, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    console.error('Error submitting query:', error);
    throw error;
  }
};

// Admin endpoints
export const getUnansweredQueries = async () => {
  try {
    const response = await api.get("/api/unanswered-queries");
    return response.data;
  } catch (error) {
    console.error('Error fetching unanswered queries:', error);
    throw error;
  }
};

export const getAdminStats = async (token) => {
  try {
    const response = await api.get('/api/admin/stats', {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching admin stats:', error);
    throw error;
  }
};

export const getAdminChatHistory = async (token) => {
  try {
    const response = await api.get('/api/admin/chat-history', {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching admin chat history:', error);
    throw error;
  }
};

export const addResponse = async (data) => {
  try {
    const response = await api.post("/api/add-response", data);
    return response.data;
  } catch (error) {
    console.error('Error adding response:', error);
    throw error;
  }
};

export const deleteQuery = async (id) => {
  try {
    const response = await api.delete(`/api/delete-query/${id}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting query:', error);
    throw error;
  }
};

export const getQueryAnalytics = async (token) => {
  try {
    const response = await api.get('/api/admin/query-analytics', {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching query analytics:', error);
    throw error;
  }
};

// Auth endpoints
export const adminLogin = async (credentials) => {
  try {
    const response = await api.post("/api/admin/login", credentials);
    return response.data;
  } catch (error) {
    console.error('Error during admin login:', error);
    throw error;
  }
};

export const userLogin = async (credentials) => {
  try {
    const response = await api.post("/api/login", credentials);
    return response.data;
  } catch (error) {
    console.error('Error during user login:', error);
    throw error;
  }
};

export const userSignup = async (userData) => {
  try {
    const response = await api.post("/api/signup", userData);
    return response.data;
  } catch (error) {
    console.error('Error during user signup:', error);
    throw error;
  }
};
