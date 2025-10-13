---
id: system.api_integration
version: 2.0
last_updated: 2025-10-13
tags: [system, api, integration, frontend, backend, websocket]
---

# API Integration Documentation

## Overview
This document provides comprehensive documentation for the API integration patterns between the Live Graphics Dashboard 2.0 frontend and backend systems, including REST APIs, WebSocket connections, and real-time data flows.

## API Architecture

### Technology Stack
- **Frontend**: Next.js 14 with TypeScript
- **Backend**: FastAPI with Python
- **API Protocol**: REST with JSON
- **Real-time**: WebSocket connections
- **Authentication**: JWT with NextAuth.js
- **API Documentation**: OpenAPI 3.0 (Swagger)

### Service Architecture
```
Frontend (Next.js) ←→ API Gateway ←→ Backend Services
                                   ↓
                            WebSocket Server
                                   ↓
                            Database Layer
                                   ↓
                          JSON Serialization Layer
```

## REST API Integration

### Base Configuration
```typescript
// lib/api/client.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.gal.gg';

interface ApiClientConfig {
  baseURL: string;
  timeout: number;
  headers: Record<string, string>;
}

class ApiClient {
  private config: ApiClientConfig;
  private baseURL: string;

  constructor(config: ApiClientConfig) {
    this.config = config;
    this.baseURL = config.baseURL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    const defaultHeaders = {
      'Content-Type': 'application/json',
      ...this.config.headers,
    };

    const response = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new ApiError(response.status, await response.json());
    }

    return response.json();
  }

  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    const url = params ? `${endpoint}?${new URLSearchParams(params)}` : endpoint;
    return this.request<T>(url, { method: 'GET' });
  }

  async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

export const apiClient = new ApiClient({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'User-Agent': 'GAL-Dashboard/2.0.0',
  },
});
```

### Authentication Integration
```typescript
// lib/api/auth.ts
import { getServerSession } from 'next-auth';
import { authOptions } from '@/app/api/auth/[...nextauth]/route';

export class AuthenticatedApiClient extends ApiClient {
  constructor() {
    super({
      baseURL: process.env.NEXT_PUBLIC_API_URL,
      timeout: 10000,
      headers: {},
    });
  }

  private async getAuthHeaders(): Promise<Record<string, string>> {
    const session = await getServerSession(authOptions);
    
    if (!session?.accessToken) {
      throw new Error('No authentication token available');
    }

    return {
      Authorization: `Bearer ${session.accessToken}`,
      'Content-Type': 'application/json',
    };
  }

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const authHeaders = await this.getAuthHeaders();
    
    return super.request<T>(endpoint, {
      ...options,
      headers: {
        ...authHeaders,
        ...options.headers,
      },
    });
  }
}

export const authenticatedApiClient = new AuthenticatedApiClient();
```

### API Error Handling
```typescript
// lib/api/errors.ts
export class ApiError extends Error {
  constructor(
    public status: number,
    public data: any,
    message?: string
  ) {
    super(message || `API Error: ${status}`);
    this.name = 'ApiError';
  }
}

export const handleApiError = (error: unknown): never => {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 401:
        throw new Error('Authentication required');
      case 403:
        throw new Error('Access denied');
      case 404:
        throw new Error('Resource not found');
      case 422:
        throw new Error('Invalid data provided');
      case 500:
        throw new Error('Server error occurred');
      default:
        throw error;
    }
  }
  throw error;
};
```

## API Endpoints

### Authentication Endpoints
```typescript
// API Endpoints for Authentication
interface AuthEndpoints {
  // Login
  'POST /auth/login': {
    request: {
      email: string;
      password: string;
      remember_me?: boolean;
    };
    response: {
      access_token: string;
      refresh_token: string;
      user: User;
      expires_in: number;
    };
  };

  // Refresh Token
  'POST /auth/refresh': {
    request: {
      refresh_token: string;
    };
    response: {
      access_token: string;
      expires_in: number;
    };
  };

  // Logout
  'POST /auth/logout': {
    request: {
      refresh_token: string;
    };
    response: {
      message: 'Successfully logged out';
    };
  };

  // User Profile
  'GET /auth/me': {
    response: User;
  };
}

// Usage Example
const login = async (credentials: LoginCredentials) => {
  try {
    const response = await apiClient.post<AuthEndpoints['POST /auth/login']['response']>(
      '/auth/login',
      credentials
    );
    return response;
  } catch (error) {
    handleApiError(error);
  }
};
```

### Graphics Management Endpoints
```typescript
// Graphics API Endpoints
interface GraphicsEndpoints {
  // List Graphics
  'GET /graphics': {
    query: {
      tournament_id?: string;
      category?: string;
      search?: string;
      page?: number;
      limit?: number;
    };
    response: {
      graphics: Graphic[];
      total: number;
      page: number;
      limit: number;
    };
  };

  // Create Graphic
  'POST /graphics': {
    request: CreateGraphicInput;
    response: Graphic;
  };

  // Get Graphic
  'GET /graphics/{id}': {
    response: Graphic;
  };

  // Update Graphic
  'PUT /graphics/{id}': {
    request: Partial<Graphic>;
    response: Graphic;
  };

  // Delete Graphic
  'DELETE /graphics/{id}': {
    response: {
      message: 'Graphic deleted successfully';
    };
  };

  // Duplicate Graphic
  'POST /graphics/{id}/duplicate': {
    request: {
      name: string;
    };
    response: Graphic;
  };
}

// Graphics API Service
export class GraphicsService {
  private api: AuthenticatedApiClient;

  constructor() {
    this.api = authenticatedApiClient;
  }

  async getGraphics(params?: GraphicsEndpoints['GET /graphics']['query']): Promise<Graphic[]> {
    const response = await this.api.get<GraphicsEndpoints['GET /graphics']['response']>(
      '/graphics',
      params
    );
    return response.graphics;
  }

  async createGraphic(data: CreateGraphicInput): Promise<Graphic> {
    return this.api.post<GraphicsEndpoints['POST /graphics']['response']>('/graphics', data);
  }

  async updateGraphic(id: string, data: Partial<Graphic>): Promise<Graphic> {
    return this.api.put<GraphicsEndpoints['PUT /graphics/{id}']['response']>(`/graphics/${id}`, data);
  }

  async deleteGraphic(id: string): Promise<void> {
    await this.api.delete<GraphicsEndpoints['DELETE /graphics/{id}']['response']>(`/graphics/${id}`);
  }

  async duplicateGraphic(id: string, name: string): Promise<Graphic> {
    return this.api.post<GraphicsEndpoints['POST /graphics/{id}/duplicate']['response']>(
      `/graphics/${id}/duplicate`,
      { name }
    );
  }
}
```

### Canvas Management Endpoints
```typescript
// Canvas API Endpoints
interface CanvasEndpoints {
  // Get Canvas
  'GET /canvases/{id}': {
    response: Canvas;
  };

  // Update Canvas
  'PUT /canvases/{id}': {
    request: Partial<Canvas>;
    response: Canvas;
  };

  // Preview Canvas
  'POST /canvases/{id}/preview': {
    request: {
      data: Record<string, any>;
    };
    response: {
      preview_url: string;
      expires_at: string;
    };
  };
}

// Canvas Service
export class CanvasService {
  private api: AuthenticatedApiClient;

  constructor() {
    this.api = authenticatedApiClient;
  }

  async getCanvas(id: string): Promise<Canvas> {
    return this.api.get<CanvasEndpoints['GET /canvases/{id}']['response']>(`/canvases/${id}`);
  }

  async updateCanvas(id: string, data: Partial<Canvas>): Promise<Canvas> {
    return this.api.put<CanvasEndpoints['PUT /canvases/{id}']['response']>(`/canvases/${id}`, data);
  }

  async previewCanvas(id: string, data: Record<string, any>): Promise<string> {
    const response = await this.api.post<CanvasEndpoints['POST /canvases/{id}/preview']['response']>(
      `/canvases/${id}/preview`,
      { data }
    );
    return response.preview_url;
  }
}
```

## WebSocket Integration

### WebSocket Client
```typescript
// lib/websocket/client.ts
export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private eventHandlers: Map<string, Function[]> = new Map();

  constructor(url: string) {
    this.url = url;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          this.send('authenticate', { token: this.getAuthToken() });
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        this.ws.onclose = () => {
          console.log('WebSocket disconnected');
          this.handleReconnect();
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  private handleMessage(message: { type: string; data: any }) {
    const handlers = this.eventHandlers.get(message.type) || [];
    handlers.forEach(handler => handler(message.data));
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      
      setTimeout(() => {
        this.connect();
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  on(event: string, handler: Function) {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, []);
    }
    this.eventHandlers.get(event)!.push(handler);
  }

  off(event: string, handler: Function) {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }

  send(type: string, data?: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }));
    } else {
      console.warn('WebSocket not connected, message not sent:', { type, data });
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private getAuthToken(): string {
    // Get authentication token from session
    return localStorage.getItem('access_token') || '';
  }
}

// WebSocket instance
export const wsClient = new WebSocketClient(
  process.env.NEXT_PUBLIC_WS_URL || 'wss://api.gal.gg/ws'
);
```

### Real-time Event Types
```typescript
// lib/websocket/events.ts
export interface WebSocketEvents {
  // Authentication Events
  'authenticated': {
    user_id: string;
    session_id: string;
  };

  // Lock Events
  'lock_acquired': {
    canvas_id: string;
    user_id: string;
    user_name: string;
    expires_at: string;
  };

  'lock_released': {
    canvas_id: string;
    user_id: string;
  };

  'lock_conflict': {
    canvas_id: string;
    current_lock: LockInfo;
    requesting_user: string;
  };

  // Graphics Events
  'graphic_created': {
    graphic: Graphic;
    created_by: string;
  };

  'graphic_updated': {
    graphic_id: string;
    updates: Partial<Graphic>;
    updated_by: string;
  };

  'graphic_deleted': {
    graphic_id: string;
    deleted_by: string;
  };

  // Canvas Events
  'canvas_updated': {
    canvas_id: string;
    updates: Partial<Canvas>;
    updated_by: string;
  };

  'cursor_moved': {
    canvas_id: string;
    user_id: string;
    position: { x: number; y: number };
  };

  // System Events
  'system_notification': {
    type: 'info' | 'warning' | 'error';
    message: string;
    timestamp: string;
  };

  'user_connected': {
    user_id: string;
    user_name: string;
  };

  'user_disconnected': {
    user_id: string;
  };
}

// Event Handler Registration
export const registerEventHandlers = () => {
  // Lock handlers
  wsClient.on('lock_acquired', (data) => {
    // Update UI to show lock status
    useLocksStore.getState().addLock(data);
  });

  wsClient.on('lock_released', (data) => {
    // Remove lock from UI
    useLocksStore.getState().removeLock(data.canvas_id);
  });

  wsClient.on('lock_conflict', (data) => {
    // Show conflict modal
    showLockConflictModal(data);
  });

  // Graphics handlers
  wsClient.on('graphic_created', (data) => {
    // Add new graphic to store
    useGraphicsStore.getState().addGraphic(data.graphic);
    showNotification(`New graphic created: ${data.graphic.name}`);
  });

  wsClient.on('graphic_updated', (data) => {
    // Update graphic in store
    useGraphicsStore.getState().updateGraphic(data.graphic_id, data.updates);
  });

  wsClient.on('graphic_deleted', (data) => {
    // Remove graphic from store
    useGraphicsStore.getState().removeGraphic(data.graphic_id);
    showNotification('Graphic deleted', 'warning');
  });

  // Canvas handlers
  wsClient.on('canvas_updated', (data) => {
    // Update canvas in store
    useCanvasStore.getState().updateCanvas(data.canvas_id, data.updates);
  });

  wsClient.on('cursor_moved', (data) => {
    // Update cursor position for collaboration
    useCanvasStore.getState().updateCursor(data.user_id, data.position);
  });

  // System handlers
  wsClient.on('system_notification', (data) => {
    // Show system notification
    showNotification(data.message, data.type);
  });
};
```

## Data Synchronization

### Optimistic Updates
```typescript
// lib/api/optimistic.ts
export class OptimisticUpdates {
  private pendingUpdates: Map<string, any> = new Map();

  async updateGraphic(id: string, updates: Partial<Graphic>): Promise<Graphic> {
    const originalGraphic = useGraphicsStore.getState().getGraphic(id);
    const optimisticGraphic = { ...originalGraphic, ...updates };

    // Optimistically update UI
    useGraphicsStore.getState().updateGraphic(id, updates);
    this.pendingUpdates.set(id, { original: originalGraphic, updates });

    try {
      const updatedGraphic = await graphicsService.updateGraphic(id, updates);
      this.pendingUpdates.delete(id);
      return updatedGraphic;
    } catch (error) {
      // Rollback on error
      useGraphicsStore.getState().updateGraphic(id, originalGraphic);
      this.pendingUpdates.delete(id);
      throw error;
    }
  }

  rollback() {
    // Rollback all pending updates
    this.pendingUpdates.forEach((value, id) => {
      useGraphicsStore.getState().updateGraphic(id, value.original);
    });
    this.pendingUpdates.clear();
  }
}
```

### Cache Management
```typescript
// lib/api/cache.ts
interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

export class ApiCache {
  private cache: Map<string, CacheEntry<any>> = new Map();
  private defaultTTL = 5 * 60 * 1000; // 5 minutes

  set<T>(key: string, data: T, ttl?: number): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl: ttl || this.defaultTTL,
    });
  }

  get<T>(key: string): T | null {
    const entry = this.cache.get(key);
    
    if (!entry) {
      return null;
    }

    if (Date.now() - entry.timestamp > entry.ttl) {
      this.cache.delete(key);
      return null;
    }

    return entry.data;
  }

  invalidate(key: string): void {
    this.cache.delete(key);
  }

  clear(): void {
    this.cache.clear();
  }

  // Cache invalidation strategies
  invalidateByPattern(pattern: string): void {
    const regex = new RegExp(pattern);
    for (const key of this.cache.keys()) {
      if (regex.test(key)) {
        this.cache.delete(key);
      }
    }
  }
}

export const apiCache = new ApiCache();
```

## React Query Integration

### Query Configuration
```typescript
// lib/api/query.ts
import { QueryClient, QueryFunction } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
    mutations: {
      retry: 1,
    },
  },
});

// Generic query fetcher
export const queryFetcher: QueryFunction = async ({ queryKey, meta }) => {
  const [endpoint, params] = queryKey as [string, Record<string, any>?];
  
  // Check cache first
  const cacheKey = `${endpoint}?${new URLSearchParams(params || {})}`;
  const cached = apiCache.get(cacheKey);
  if (cached && !meta?.skipCache) {
    return cached;
  }

  // Fetch from API
  const data = await authenticatedApiClient.get(endpoint, params);
  
  // Cache result
  apiCache.set(cacheKey, data);
  
  return data;
};

// Query hooks
export const useGraphics = (params?: GraphicsQueryParams) => {
  return useQuery({
    queryKey: ['/graphics', params],
    queryFn: queryFetcher,
    select: (data: any) => data.graphics,
  });
};

export const useGraphic = (id: string) => {
  return useQuery({
    queryKey: ['/graphics', id],
    queryFn: () => authenticatedApiClient.get(`/graphics/${id}`),
    enabled: !!id,
  });
};
```

## Real-time Data Flow

### Data Flow Architecture
```
User Action → Frontend State → API Request → Backend Processing
     ↓              ↓              ↓              ↓
UI Update ← WebSocket Event ← Database Update ← Backend Event
```

### State Synchronization
```typescript
// lib/store/sync.ts
export class StateSynchronizer {
  constructor() {
    this.setupWebSocketListeners();
    this.setupQueryInvalidation();
  }

  private setupWebSocketListeners() {
    // Listen for WebSocket events and invalidate relevant queries
    wsClient.on('graphic_created', (data) => {
      queryClient.invalidateQueries({ queryKey: ['/graphics'] });
    });

    wsClient.on('graphic_updated', (data) => {
      queryClient.invalidateQueries({ queryKey: ['/graphics', data.graphic_id] });
      queryClient.invalidateQueries({ queryKey: ['/graphics'] });
    });

    wsClient.on('graphic_deleted', (data) => {
      queryClient.invalidateQueries({ queryKey: ['/graphics', data.graphic_id] });
      queryClient.invalidateQueries({ queryKey: ['/graphics'] });
    });
  }

  private setupQueryInvalidation() {
    // Invalidate cache on mutations
    queryClient.setMutationDefaults(['createGraphic'], {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['/graphics'] });
      },
    });

    queryClient.setMutationDefaults(['updateGraphic'], {
      onSuccess: (data, variables) => {
        queryClient.invalidateQueries({ queryKey: ['/graphics', variables.id] });
        queryClient.invalidateQueries({ queryKey: ['/graphics'] });
      },
    });

    queryClient.setMutationDefaults(['deleteGraphic'], {
      onSuccess: (_, variables) => {
        queryClient.invalidateQueries({ queryKey: ['/graphics', variables.id] });
        queryClient.invalidateQueries({ queryKey: ['/graphics'] });
      },
    });
  }
}

export const stateSynchronizer = new StateSynchronizer();
```

## Error Handling and Recovery

### API Error Recovery
```typescript
// lib/api/recovery.ts
export class ApiRecovery {
  private retryQueue: Array<() => Promise<any>> = [];
  private isRecovering = false;

  async enqueueRetry(operation: () => Promise<any>): Promise<any> {
    if (this.isRecovering) {
      return new Promise((resolve, reject) => {
        this.retryQueue.push(async () => {
          try {
            const result = await operation();
            resolve(result);
          } catch (error) {
            reject(error);
          }
        });
      });
    }

    return operation();
  }

  async startRecovery() {
    this.isRecovering = true;
    
    try {
      // Clear cache
      apiCache.clear();
      
      // Reconnect WebSocket
      await wsClient.connect();
      
      // Retry queued operations
      const operations = [...this.retryQueue];
      this.retryQueue = [];
      
      for (const operation of operations) {
        await operation();
      }
    } finally {
      this.isRecovering = false;
    }
  }
}

export const apiRecovery = new ApiRecovery();
```

## JSON Serialization Handling

### Overview
Due to SQLite limitations, complex data structures must be serialized to JSON strings before database storage and deserialized after retrieval. This section documents the JSON serialization patterns used in the Live Graphics Dashboard API integration.

### Graphics Data Serialization

#### Backend Implementation
```python
# api/services/graphics_service.py
import json
from typing import Dict, Any

class GraphicsService:
    def create_graphic(self, graphic: GraphicCreate, created_by: str) -> Dict[str, Any]:
        """Create a new graphic with proper JSON serialization"""
        from ..models import Graphic
        
        db_graphic = Graphic(
            title=graphic.title,
            # Serialize Python dict to JSON string for SQLite compatibility
            data_json=json.dumps(graphic.data_json or {}),
            created_by=created_by,
            archived=False
        )
        
        self.db.add(db_graphic)
        self.db.commit()
        self.db.refresh(db_graphic)
        
        return {
            "id": db_graphic.id,
            "title": db_graphic.title,
            # Deserialize JSON string back to Python dict for API response
            "data_json": json.loads(db_graphic.data_json) if db_graphic.data_json else {},
            "created_by": db_graphic.created_by,
            "created_at": db_graphic.created_at,
            "updated_at": db_graphic.updated_at,
            "archived": db_graphic.archived
        }
    
    def get_graphic_by_id(self, graphic_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve graphic with proper JSON deserialization"""
        from ..models import Graphic
        
        graphic = self.db.query(Graphic).filter(Graphic.id == graphic_id).first()
        
        if not graphic:
            return None
        
        return {
            "id": graphic.id,
            "title": graphic.title,
            # Handle potential eval() usage from legacy code
            "data_json": eval(graphic.data_json) if graphic.data_json else {},
            "created_by": graphic.created_by,
            "created_at": graphic.created_at,
            "updated_at": graphic.updated_at,
            "archived": graphic.archived
        }
    
    def update_graphic(self, graphic_id: int, graphic_update: GraphicUpdate, user_name: str) -> Optional[Dict[str, Any]]:
        """Update graphic with JSON serialization"""
        from ..models import Graphic
        
        graphic = self.db.query(Graphic).filter(Graphic.id == graphic_id).first()
        
        if not graphic:
            return None
        
        if graphic_update.title is not None:
            graphic.title = graphic_update.title
        
        if graphic_update.data_json is not None:
            # Serialize updated data to JSON string
            graphic.data_json = json.dumps(graphic_update.data_json)
        
        graphic.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(graphic)
        
        return {
            "id": graphic.id,
            "title": graphic.title,
            "data_json": eval(graphic.data_json) if graphic.data_json else {},
            "created_by": graphic.created_by,
            "created_at": graphic.created_at,
            "updated_at": graphic.updated_at,
            "archived": graphic.archived
        }
```

#### Frontend Integration
```typescript
// dashboard/hooks/use-graphics.ts
import { useState, useEffect, useCallback } from 'react';
import { Graphic, CreateGraphicRequest, UpdateGraphicRequest } from '@/types';
import { graphicsApi } from '@/lib/api';

export function useGraphics() {
  const [graphics, setGraphics] = useState<Graphic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const createGraphic = useCallback(async (data: CreateGraphicRequest): Promise<Graphic | null> => {
    try {
      // Frontend sends data_json as object, backend handles serialization
      const newGraphic = await graphicsApi.create(data);
      setGraphics(prev => [newGraphic, ...prev]);
      return newGraphic;
    } catch (err) {
      setError('Failed to create graphic');
      console.error('Error creating graphic:', err);
      return null;
    }
  }, []);

  const updateGraphic = useCallback(async (id: number, data: UpdateGraphicRequest): Promise<Graphic | null> => {
    try {
      // Frontend can send data_json as string or object
      const updatedGraphic = await graphicsApi.update(id, data);
      setGraphics(prev => 
        prev.map(g => g.id === id ? updatedGraphic : g)
      );
      return updatedGraphic;
    } catch (err) {
      setError('Failed to update graphic');
      console.error('Error updating graphic:', err);
      return null;
    }
  }, []);

  return {
    graphics,
    loading,
    error,
    createGraphic,
    updateGraphic,
    // ... other methods
  };
}
```

### Type Definitions
```typescript
// dashboard/types/index.ts
export interface CreateGraphicRequest {
  title: string;
  data_json?: any; // JSON object - frontend sends as object, backend serializes
}

export interface UpdateGraphicRequest {
  title?: string;
  data_json?: string; // JSON string - can be either string or object
}

export interface Graphic {
  id: number;
  title: string;
  data_json: string; // JSON string from backend, parsed in frontend
  created_by: string;
  updated_at: string;
  archived: boolean;
  canvas_lock?: CanvasLock;
}
```

### API Client Implementation
```typescript
// dashboard/lib/api.ts
export const graphicsApi = {
  create: async (data: CreateGraphicRequest): Promise<Graphic> => {
    const response: AxiosResponse<Graphic> = await api.post('/graphics', data);
    return response.data;
  },

  update: async (id: number, data: UpdateGraphicRequest): Promise<Graphic> => {
    const response: AxiosResponse<Graphic> = await api.put(`/graphics/${id}`, data);
    return response.data;
  },

  getAll: async (): Promise<Graphic[]> => {
    const response: AxiosResponse<Graphic[]> = await api.get('/graphics');
    return response.data.map(graphic => ({
      ...graphic,
      // Ensure data_json is properly handled on frontend
      data_json: typeof graphic.data_json === 'string' 
        ? graphic.data_json 
        : JSON.stringify(graphic.data_json)
    }));
  }
};
```

### Frontend Component Usage
```typescript
// dashboard/components/graphics/GraphicsTab.tsx
const handleCreateGraphic = useCallback(async (data: { title: string }) => {
  try {
    const canvasData = {
      elements: [],
      settings: {
        width: 1920,
        height: 1080,
        backgroundColor: '#000000'
      }
    };
    
    // Send data_json as object - backend will serialize
    const result = await createGraphic({
      title: data.title,
      data_json: canvasData, // Object, not string
      created_by: username || 'Dashboard User'
    });
    return !!result;
  } catch (error) {
    console.error('Failed to create graphic:', error);
    return false;
  }
}, [createGraphic]);

const handleSaveGraphic = useCallback(async (data: { title: string; data_json: string }) => {
  if (!editingGraphic) return false;
  
  try {
    // Canvas editor sends data_json as string - backend handles as-is
    const result = await updateGraphic(editingGraphic.id, data);
    return !!result;
  } catch (error) {
    console.error('Failed to update graphic:', error);
    return false;
  }
}, [editingGraphic, updateGraphic]);
```

### Error Handling and Validation

#### JSON Serialization Error Handling
```typescript
// lib/api/validation.ts
export function validateGraphicData(data: any): boolean {
  try {
    // Validate data structure
    if (!data || typeof data !== 'object') {
      return false;
    }
    
    // Check for required fields
    if (data.elements && !Array.isArray(data.elements)) {
      return false;
    }
    
    if (data.settings && typeof data.settings !== 'object') {
      return false;
    }
    
    return true;
  } catch (error) {
    console.error('Graphic data validation error:', error);
    return false;
  }
}

export function safeJsonParse(jsonString: string): any {
  try {
    return JSON.parse(jsonString);
  } catch (error) {
    console.error('JSON parse error:', error);
    return {};
  }
}
```

#### Backend Error Handling
```python
# api/services/graphics_service.py
def create_graphic(self, graphic: GraphicCreate, created_by: str) -> Dict[str, Any]:
    """Create a new graphic with robust error handling"""
    try:
        from ..models import Graphic
        
        # Validate data_json before serialization
        data_to_serialize = graphic.data_json or {}
        
        # Ensure data is JSON serializable
        try:
            json_str = json.dumps(data_to_serialize)
        except (TypeError, ValueError) as e:
            logger.error(f"JSON serialization error: {e}")
            json_str = json.dumps({})  # Fallback to empty object
        
        db_graphic = Graphic(
            title=graphic.title,
            data_json=json_str,
            created_by=created_by,
            archived=False
        )
        
        self.db.add(db_graphic)
        self.db.commit()
        self.db.refresh(db_graphic)
        
        return {
            "id": db_graphic.id,
            "title": db_graphic.title,
            "data_json": json.loads(db_graphic.data_json) if db_graphic.data_json else {},
            "created_by": db_graphic.created_by,
            "created_at": db_graphic.created_at,
            "updated_at": db_graphic.updated_at,
            "archived": db_graphic.archived
        }
        
    except Exception as e:
        logger.error(f"Error creating graphic: {e}")
        self.db.rollback()
        raise
```

### Migration Notes

#### Legacy Code Handling
The system may contain legacy code using `eval()` for JSON deserialization. This is being phased out in favor of `json.loads()`:

```python
# Legacy approach (being replaced)
"data_json": eval(graphic.data_json) if graphic.data_json else {},

# New approach (preferred)
"data_json": json.loads(graphic.data_json) if graphic.data_json else {},
```

#### Data Migration Strategy
1. **Gradual Migration**: Update create/update operations first
2. **Data Validation**: Implement validation before migration
3. **Backward Compatibility**: Support both formats during transition
4. **Testing**: Comprehensive testing of serialization/deserialization
5. **Monitoring**: Monitor for serialization errors in production

### Best Practices

1. **Consistent Serialization**: Always use `json.dumps()` for database storage
2. **Proper Deserialization**: Always use `json.loads()` for API responses
3. **Error Handling**: Implement robust error handling for JSON operations
4. **Data Validation**: Validate data structure before serialization
5. **Type Safety**: Use TypeScript interfaces for frontend data structures
6. **Testing**: Test with various data types and edge cases

## Performance Optimization

### Request Debouncing
```typescript
// lib/api/debounce.ts
export class Debouncer {
  private timers: Map<string, NodeJS.Timeout> = new Map();

  debounce<T>(key: string, fn: () => Promise<T>, delay: number): Promise<T> {
    return new Promise((resolve, reject) => {
      // Clear existing timer
      if (this.timers.has(key)) {
        clearTimeout(this.timers.get(key)!);
      }

      // Set new timer
      const timer = setTimeout(async () => {
        try {
          const result = await fn();
          resolve(result);
        } catch (error) {
          reject(error);
        } finally {
          this.timers.delete(key);
        }
      }, delay);

      this.timers.set(key, timer);
    });
  }
}

export const debouncer = new Debouncer();

// Usage example
const debouncedSaveCanvas = (canvasId: string, updates: Partial<Canvas>) => {
  return debouncer.debounce(
    `canvas-${canvasId}`,
    () => canvasService.updateCanvas(canvasId, updates),
    1000 // 1 second debounce
  );
};
```

### Request Batching
```typescript
// lib/api/batch.ts
interface BatchRequest {
  id: string;
  method: string;
  endpoint: string;
  data?: any;
}

interface BatchResponse {
  id: string;
  data?: any;
  error?: string;
}

export class BatchProcessor {
  private queue: BatchRequest[] = [];
  private timer: NodeJS.Timeout | null = null;
  private readonly batchSize = 10;
  private readonly batchDelay = 100; // 100ms

  add(request: BatchRequest): Promise<BatchResponse> {
    return new Promise((resolve, reject) => {
      this.queue.push({
        ...request,
        resolve,
        reject,
      } as any);

      this.scheduleBatch();
    });
  }

  private scheduleBatch() {
    if (this.timer) {
      return;
    }

    this.timer = setTimeout(() => {
      this.processBatch();
      this.timer = null;
    }, this.batchDelay);

    if (this.queue.length >= this.batchSize) {
      clearTimeout(this.timer!);
      this.processBatch();
      this.timer = null;
    }
  }

  private async processBatch() {
    const batch = this.queue.splice(0, this.batchSize);
    
    try {
      const response = await authenticatedApiClient.post<BatchResponse[]>('/batch', {
        requests: batch.map(({ resolve, reject, ...req }) => req),
      });

      response.forEach((resp, index) => {
        const request = batch[index] as any;
        if (resp.error) {
          request.reject(new Error(resp.error));
        } else {
          request.resolve(resp);
        }
      });
    } catch (error) {
      batch.forEach((request: any) => {
        request.reject(error);
      });
    }
  }
}

export const batchProcessor = new BatchProcessor();
```

## Testing

### API Testing
```typescript
// __tests__/api.test.ts
describe('API Integration', () => {
  beforeEach(() => {
    // Setup test environment
    setupApiMocks();
  });

  test('should fetch graphics successfully', async () => {
    const graphics = await graphicsService.getGraphics();
    
    expect(graphics).toHaveLength(2);
    expect(graphics[0]).toMatchObject({
      id: expect.any(String),
      name: expect.any(String),
      template_id: expect.any(String),
    });
  });

  test('should create graphic successfully', async () => {
    const newGraphic = await graphicsService.createGraphic({
      name: 'Test Graphic',
      template_id: 'template-1',
      data: {},
    });

    expect(newGraphic).toMatchObject({
      id: expect.any(String),
      name: 'Test Graphic',
      template_id: 'template-1',
    });
  });

  test('should handle API errors correctly', async () => {
    await expect(
      graphicsService.getGraphic('invalid-id')
    ).rejects.toThrow('Resource not found');
  });
});

// WebSocket Testing
describe('WebSocket Integration', () => {
  test('should receive lock events', (done) => {
    wsClient.on('lock_acquired', (data) => {
      expect(data).toMatchObject({
        canvas_id: expect.any(String),
        user_id: expect.any(String),
      });
      done();
    });

    // Simulate lock event
    simulateWebSocketEvent('lock_acquired', {
      canvas_id: 'canvas-1',
      user_id: 'user-1',
      user_name: 'Test User',
      expires_at: new Date().toISOString(),
    });
  });
});
```

## Security Considerations

### Request Security
```typescript
// lib/api/security.ts
export class ApiSecurity {
  private static instance: ApiSecurity;
  private csrfToken: string | null = null;

  static getInstance(): ApiSecurity {
    if (!ApiSecurity.instance) {
      ApiSecurity.instance = new ApiSecurity();
    }
    return ApiSecurity.instance;
  }

  async getCsrfToken(): Promise<string> {
    if (!this.csrfToken) {
      const response = await fetch('/api/csrf-token');
      const data = await response.json();
      this.csrfToken = data.token;
    }
    return this.csrfToken;
  }

  async secureRequest(url: string, options: RequestInit = {}): Promise<Response> {
    const secureHeaders = {
      'X-CSRF-Token': await this.getCsrfToken(),
      'X-Requested-With': 'XMLHttpRequest',
      ...options.headers,
    };

    return fetch(url, {
      ...options,
      headers: secureHeaders,
      credentials: 'include',
    });
  }

  sanitizeInput(input: any): any {
    if (typeof input === 'string') {
      return input
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#x27;');
    }
    
    if (Array.isArray(input)) {
      return input.map(item => this.sanitizeInput(item));
    }
    
    if (typeof input === 'object' && input !== null) {
      const sanitized: any = {};
      for (const [key, value] of Object.entries(input)) {
        sanitized[key] = this.sanitizeInput(value);
      }
      return sanitized;
    }
    
    return input;
  }
}

export const apiSecurity = ApiSecurity.getInstance();
```

## References
- [REST API Documentation](../system/api-backend-system.md)
- [WebSocket Documentation](../system/websocket-integration.md)
- [Authentication Documentation](../system/authentication.md)
- [React Query Documentation](https://tanstack.com/query/latest)
- [Next.js API Routes](https://nextjs.org/docs/api-routes/introduction)

## Document Control
- **Version**: 1.0
- **Created**: 2025-01-11
- **Review Date**: 2025-04-11
- **Next Review**: 2025-07-11
- **Approved By**: API Architect
- **Classification**: Internal Use Only
