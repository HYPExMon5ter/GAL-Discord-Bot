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

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 
  (process.env.NODE_ENV === 'production' 
    ? '/api/v1' 
    : 'http://localhost:8000/api/v1');

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
    const response: AxiosResponse<AuthResponse> = await axios.post(`${API_BASE_URL.replace('/api/v1', '')}/auth/login`, data);
    return response.data;
  },

  logout: async (): Promise<void> => {
    await axios.post(`${API_BASE_URL.replace('/api/v1', '')}/auth/logout`);
  },
};

export const graphicsApi = {
  getAll: async (): Promise<Graphic[]> => {
    const response: AxiosResponse<{graphics: Graphic[]}> = await api.get('/graphics');
    return response.data.graphics;
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

  duplicate: async (id: number, newTitle?: string, newEventName?: string): Promise<Graphic> => {
    const response: AxiosResponse<Graphic> = await api.post(`/graphics/${id}/duplicate`, {
      new_title: newTitle,
      new_event_name: newEventName
    });
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/graphics/${id}`);
  },

  permanentDelete: async (id: number): Promise<void> => {
    await api.delete(`/graphics/${id}/permanent`);
  },

  archive: async (id: number): Promise<void> => {
    await api.post(`/archive/${id}`, {});
  },
};

export const archiveApi = {
  getAll: async (): Promise<ArchivedGraphic[]> => {
    const response: AxiosResponse<{archives: ArchivedGraphic[]}> = await api.get('/archive');
    return response.data.archives;
  },

  restore: async (id: number): Promise<void> => {
    await api.post(`/archive/${id}/restore`);
  },

  permanentDelete: async (id: number): Promise<void> => {
    await api.delete(`/archive/${id}/permanent`);
  },
  copyFromArchived: async (id: number, title: string, eventName?: string): Promise<Graphic> => {
    const response: AxiosResponse<Graphic> = await api.post(`/graphics/${id}/duplicate`, {
      new_title: title,
      new_event_name: eventName
    });
    return response.data;
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
    const response: AxiosResponse<CanvasLock> = await api.post(`/lock/${graphicId}/refresh`);
    return response.data;
  },
};

export const playerApi = {
  getRankedPlayers: async (options?: {
    tournamentId?: string;
    guildId?: string;
    sortBy?: string;
    sortOrder?: string;
    limit?: number;
  }) => {
    const params = new URLSearchParams();
    
    if (options?.tournamentId) params.append('tournament_id', options.tournamentId);
    if (options?.guildId) params.append('guild_id', options.guildId);
    if (options?.sortBy) params.append('sort_by', options.sortBy);
    if (options?.sortOrder) params.append('sort_order', options.sortOrder);
    if (options?.limit) params.append('limit', options.limit.toString());
    
    const response: AxiosResponse<{
      players: Array<{
        player_name: string;
        total_points: number;
        standing_rank: number;
        player_id?: string;
        discord_id?: string;
        riot_id?: string;
        round_scores?: Record<string, number>;
      }>;
      total: number;
      snapshot_id?: number;
      snapshot_created_at?: string;
      tournament_id?: string;
      tournament_name?: string;
    }> = await api.get(`/players/ranked?${params.toString()}`);
    
    return response.data;
  },
};

export default api;
