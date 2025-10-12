import axios, { AxiosResponse } from 'axios';
import { 
  Graphic, 
  CanvasLock, 
  ArchivedGraphic, 
  AuthResponse, 
  LoginRequest, 
  CreateGraphicRequest, 
  UpdateGraphicRequest,
  ApiResponse 
} from '@/types';

const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? '/api' 
  : 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false,
});

// Add request interceptor to include auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Add response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('username');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  login: async (data: LoginRequest): Promise<AuthResponse> => {
    const response: AxiosResponse<AuthResponse> = await api.post('/auth/login', data);
    return response.data;
  },

  logout: async (): Promise<void> => {
    await api.post('/auth/logout');
  },
};

export const graphicsApi = {
  getAll: async (): Promise<Graphic[]> => {
    const response: AxiosResponse<Graphic[]> = await api.get('/graphics');
    return response.data;
  },

  getById: async (id: number): Promise<Graphic> => {
    const response: AxiosResponse<Graphic> = await api.get(`/graphics/${id}`);
    return response.data;
  },

  create: async (data: CreateGraphicRequest): Promise<Graphic> => {
    const response: AxiosResponse<Graphic> = await api.post('/graphics', data);
    return response.data;
  },

  update: async (id: number, data: UpdateGraphicRequest): Promise<Graphic> => {
    const response: AxiosResponse<Graphic> = await api.put(`/graphics/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/graphics/${id}`);
  },

  archive: async (id: number): Promise<void> => {
    await api.post(`/archive/${id}`);
  },
};

export const archiveApi = {
  getAll: async (): Promise<ArchivedGraphic[]> => {
    const response: AxiosResponse<ArchivedGraphic[]> = await api.get('/archive');
    return response.data;
  },

  restore: async (id: number): Promise<void> => {
    await api.post(`/archive/${id}/restore`);
  },

  permanentDelete: async (id: number): Promise<void> => {
    await api.delete(`/archive/${id}`);
  },
};

export const lockApi = {
  acquire: async (graphicId: number): Promise<CanvasLock> => {
    const response: AxiosResponse<CanvasLock> = await api.post(`/lock/${graphicId}`);
    return response.data;
  },

  release: async (graphicId: number): Promise<void> => {
    await api.delete(`/lock/${graphicId}`);
  },

  getStatus: async (graphicId?: number): Promise<CanvasLock[]> => {
    const url = graphicId ? `/lock/status?graphic_id=${graphicId}` : '/lock/status';
    const response: AxiosResponse<CanvasLock[]> = await api.get(url);
    return response.data;
  },

  refresh: async (graphicId: number): Promise<CanvasLock> => {
    const response: AxiosResponse<CanvasLock> = await api.put(`/lock/${graphicId}`);
    return response.data;
  },
};

export default api;
