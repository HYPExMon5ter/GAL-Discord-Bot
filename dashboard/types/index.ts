export interface Graphic {
  id: number;
  title: string;
  event_name?: string;
  data_json: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  archived: boolean;
  canvas_lock?: CanvasLock;
}

export interface CanvasLock {
  id: number;
  graphic_id: number;
  locked: boolean;
  locked_at: string;
  expires_at: string;
}

export interface ArchivedGraphic extends Graphic {
  archived_at: string;
  restored_from?: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginRequest {
  master_password: string;
}

export interface CreateGraphicRequest {
  title: string;
  event_name?: string;
  data_json?: any; // JSON object, not string
}

export interface UpdateGraphicRequest {
  title?: string;
  event_name?: string;
  data_json?: string;
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

// Export clean canvas types from new location
export type {
  CanvasState,
  BackgroundConfig,
  ElementType,
  BaseElement,
  TextElement,
  DynamicElement,
  CanvasElement,
  PlayerData,
  ElementDefaults
} from '@/lib/canvas/types';

export { DEFAULT_ELEMENT_CONFIGS, DEFAULT_PREVIEW_COUNT, DEFAULT_SPACING } from '@/lib/canvas/types';
