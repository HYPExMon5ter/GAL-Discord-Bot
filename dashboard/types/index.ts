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
  user_name: string;
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

export type CanvasElementType = 'text' | 'player' | 'score' | 'placement';

export type CanvasPropertyType = Extract<CanvasElementType, 'player' | 'score' | 'placement'>;

export interface CanvasDataBinding {
  source: 'api' | 'manual';
  field: 'player_name' | 'player_score' | 'player_placement' | 'player_rank' | 'team_name';
  apiEndpoint?: string | null;
  manualValue?: string | null;
}

export interface CanvasElementStyle {
  fontSize?: number;
  fontFamily?: string;
  color?: string;
  backgroundColor?: string;
  borderColor?: string;
  borderWidth?: number;
  borderRadius?: number;
}

export interface CanvasElement extends CanvasElementStyle {
  id: string;
  type: CanvasElementType;
  content?: string;
  placeholderText?: string;
  x: number;
  y: number;
  width?: number;
  height?: number;
  dataBinding?: CanvasDataBinding | null;
  isPlaceholder?: boolean;
}

export interface CanvasSettings {
  width: number;
  height: number;
  backgroundColor: string;
}

export interface CanvasState {
  elements: CanvasElement[];
  settings: CanvasSettings;
  backgroundImage?: string | null;
}

export interface SnapLine {
  x?: number;
  y?: number;
}
