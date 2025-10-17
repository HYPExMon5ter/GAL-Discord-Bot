---
id: sops.frontend-api-structure-sop
version: 1.0
last_updated: 2025-01-17
tags: [frontend, api, development, sop, structure]
status: production
---

# Frontend API Structure SOP

## Overview

This SOP outlines the procedures for managing the frontend API structure located in `dashboard/api/`. This directory provides frontend-specific API utilities, services, and abstractions for interacting with the backend API.

## Directory Structure

### Organization

```
dashboard/api/
├── services/          # API service classes and utilities
│   ├── graphics.ts    # Graphics management service
│   ├── auth.ts        # Authentication service
│   └── locks.ts       # Canvas locking service
└── utils/             # API utility functions and helpers
    ├── client.ts      # HTTP client configuration
    ├── types.ts       # TypeScript type definitions
    └── validation.ts  # Data validation utilities
```

### Purpose

The frontend API structure provides:
- **Service Abstractions**: High-level APIs for different feature areas
- **Type Safety**: TypeScript interfaces for all API interactions
- **Error Handling**: Consistent error management across API calls
- **Data Validation**: Client-side validation before API calls
- **HTTP Client Configuration**: Centralized HTTP client setup

## Development Procedures

### Creating New API Services

#### Service Structure Template

```typescript
// dashboard/api/services/[service-name].ts
import { apiClient } from '../utils/client';
import { ApiResponse, ApiError } from '../utils/types';

export interface [ServiceName]Data {
  // Define service-specific data types
}

export class [ServiceName]Service {
  private baseUrl = '/api/v1/[service-name]';

  async getAll(): Promise<[ServiceName]Data[]> {
    try {
      const response = await apiClient.get(`${this.baseUrl}`);
      return response.data;
    } catch (error) {
      throw new ApiError('Failed to fetch [service-name] data', error);
    }
  }

  async create(data: Partial<[ServiceName]Data>): Promise<[ServiceName]Data> {
    try {
      const response = await apiClient.post(`${this.baseUrl}`, data);
      return response.data;
    } catch (error) {
      throw new ApiError('Failed to create [service-name]', error);
    }
  }

  async update(id: number, data: Partial<[ServiceName]Data>): Promise<[ServiceName]Data> {
    try {
      const response = await apiClient.put(`${this.baseUrl}/${id}`, data);
      return response.data;
    } catch (error) {
      throw new ApiError('Failed to update [service-name]', error);
    }
  }

  async delete(id: number): Promise<void> {
    try {
      await apiClient.delete(`${this.baseUrl}/${id}`);
    } catch (error) {
      throw new ApiError('Failed to delete [service-name]', error);
    }
  }
}
```

#### Service Implementation Steps

1. **Create Service File**: Add new service in `dashboard/api/services/`
2. **Define Interfaces**: Create TypeScript interfaces for data structures
3. **Implement Methods**: Add CRUD operations following the template
4. **Add Error Handling**: Implement consistent error management
5. **Update Exports**: Add service to index file exports
6. **Write Tests**: Create unit tests for the service

### API Client Configuration

#### HTTP Client Setup

```typescript
// dashboard/api/utils/client.ts
import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { getAuthToken } from './auth';

export const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for authentication
apiClient.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

### Type Definitions

#### Standard API Types

```typescript
// dashboard/api/utils/types.ts
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: number;
}

export interface ApiError {
  message: string;
  code?: string;
  details?: any;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
  hasPrev: boolean;
}

// Generic CRUD interfaces
export interface CreateRequest<T> {
  data: Partial<T>;
}

export interface UpdateRequest<T> {
  id: number;
  data: Partial<T>;
}

export interface DeleteRequest {
  id: number;
}
```

## Service Examples

### Graphics Service Implementation

```typescript
// dashboard/api/services/graphics.ts
import { apiClient } from '../utils/client';
import { ApiResponse, PaginatedResponse } from '../utils/types';

export interface Graphic {
  id: number;
  title: string;
  event_name: string;
  data_json: Record<string, any>;
  created_by: string;
  created_at: string;
  updated_at: string;
  is_locked: boolean;
}

export interface GraphicCreate {
  title: string;
  event_name: string;
  data_json: Record<string, any>;
}

export interface GraphicUpdate {
  title?: string;
  event_name?: string;
  data_json?: Record<string, any>;
}

export class GraphicsService {
  private baseUrl = '/api/v1/graphics';

  async getGraphics(options?: {
    page?: number;
    pageSize?: number;
    search?: string;
  }): Promise<PaginatedResponse<Graphic>> {
    const params = new URLSearchParams();
    
    if (options?.page) params.append('page', options.page.toString());
    if (options?.pageSize) params.append('pageSize', options.pageSize.toString());
    if (options?.search) params.append('search', options.search);

    const response = await apiClient.get(`${this.baseUrl}?${params}`);
    return response.data;
  }

  async createGraphic(data: GraphicCreate): Promise<Graphic> {
    const response = await apiClient.post(this.baseUrl, data);
    return response.data;
  }

  async updateGraphic(id: number, data: GraphicUpdate): Promise<Graphic> {
    const response = await apiClient.put(`${this.baseUrl}/${id}`, data);
    return response.data;
  }

  async deleteGraphic(id: number): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${id}`);
  }

  async getGraphic(id: number): Promise<Graphic> {
    const response = await apiClient.get(`${this.baseUrl}/${id}`);
    return response.data;
  }
}

export const graphicsService = new GraphicsService();
```

## Integration Procedures

### Using Services in Components

#### React Hook Pattern

```typescript
// dashboard/hooks/use-graphics.ts
import { useState, useEffect } from 'react';
import { graphicsService, Graphic } from '../api/services/graphics';
import { ApiError } from '../api/utils/types';

export function useGraphics() {
  const [graphics, setGraphics] = useState<Graphic[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const loadGraphics = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await graphicsService.getGraphics();
      setGraphics(response.items);
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setLoading(false);
    }
  };

  const createGraphic = async (data: Parameters<typeof graphicsService.createGraphic>[0]) => {
    try {
      const newGraphic = await graphicsService.createGraphic(data);
      setGraphics(prev => [...prev, newGraphic]);
      return newGraphic;
    } catch (err) {
      setError(err as ApiError);
      throw err;
    }
  };

  useEffect(() => {
    loadGraphics();
  }, []);

  return {
    graphics,
    loading,
    error,
    loadGraphics,
    createGraphic,
  };
}
```

## Testing Procedures

### Unit Testing Services

```typescript
// __tests__/api/services/graphics.test.ts
import { GraphicsService } from '../../api/services/graphics';
import { apiClient } from '../../api/utils/client';
import { Graphic } from '../../api/services/graphics';

jest.mock('../../api/utils/client');
const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('GraphicsService', () => {
  let graphicsService: GraphicsService;

  beforeEach(() => {
    graphicsService = new GraphicsService();
    jest.clearAllMocks();
  });

  describe('getGraphics', () => {
    it('should fetch graphics successfully', async () => {
      const mockGraphics: Graphic[] = [
        { id: 1, title: 'Test Graphic', event_name: 'Test Event', 
          data_json: {}, created_by: 'user', created_at: '2024-01-01', 
          updated_at: '2024-01-01', is_locked: false }
      ];

      mockedApiClient.get.mockResolvedValue({
        data: { items: mockGraphics, total: 1, page: 1, pageSize: 10, hasNext: false, hasPrev: false }
      });

      const result = await graphicsService.getGraphics();

      expect(mockedApiClient.get).toHaveBeenCalledWith('/api/v1/graphics?page=1&pageSize=10');
      expect(result.items).toEqual(mockGraphics);
    });
  });
});
```

## Maintenance Procedures

### Updating API Endpoints

1. **Review Changes**: Check backend API documentation for updates
2. **Update Service Methods**: Modify service methods to match new endpoints
3. **Update Type Definitions**: Adjust TypeScript interfaces as needed
4. **Update Tests**: Modify unit tests to reflect changes
5. **Test Integration**: Verify frontend components work correctly

### Adding New Endpoints

1. **Add Service Method**: Implement new endpoint in appropriate service
2. **Define Types**: Create TypeScript interfaces for request/response
3. **Add Validation**: Implement client-side validation if needed
4. **Write Tests**: Create unit tests for new functionality
5. **Update Documentation**: Document the new endpoint usage

### Error Handling Updates

1. **Review Error Patterns**: Check for new error types from backend
2. **Update Error Classes**: Add new error types if needed
3. **Update Error Handling**: Modify service error handling logic
4. **Update UI Error Messages**: Add user-friendly error messages
5. **Test Error Scenarios**: Verify error handling works correctly

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Check import paths in service files
# Ensure proper TypeScript configuration
npm run type-check
```

**API Client Configuration**
```bash
# Verify environment variables
echo $NEXT_PUBLIC_API_BASE_URL

# Check CORS configuration
# Review backend CORS settings
```

**Type Mismatches**
```bash
# Run TypeScript compiler to find issues
npm run type-check

# Check interface definitions match backend schemas
```

## Related Documentation

- [API Integration Documentation](../system/api-integration.md)
- [Frontend Components Documentation](../system/frontend-components.md)
- [TypeScript Configuration](../system/developer-documentation.md)
- [Dashboard Operations SOP](../sops/dashboard-operations.md)

---

**Status**: Draft - Ready for Review  
**Next Steps**: Implement service structure and add comprehensive testing  
**Maintainer**: Frontend Development Team
