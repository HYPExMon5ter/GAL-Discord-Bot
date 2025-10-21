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

// Simplified element system types
export interface ElementSeries {
  id: string;
  type: CanvasPropertyType;
  baseElement: CanvasElement; // The first placed element
  spacing: ElementSpacing;
  autoGenerate: boolean;
  maxElements?: number;
  sortBy: 'total_points' | 'player_name' | 'standing_rank';
  sortOrder: 'asc' | 'desc';
}

export interface ElementSpacing {
  horizontal: number;
  vertical: number;
  direction: 'horizontal' | 'vertical' | 'grid';
}

export interface CanvasDataBinding {
  source: 'api' | 'manual' | 'series' | 'dataset';
  field: 'player_name' | 'player_score' | 'player_placement' | 'player_rank' | 'team_name' | 'round_score';
  apiEndpoint?: string | null;
  manualValue?: string | null;
  seriesId?: string | null; // Reference to element series for auto-generation
  fallbackText?: string | null; // Fallback text for dataset bindings
  dataset?: CanvasDatasetBinding | null; // For backward compatibility
}

// Legacy types for backward compatibility
export interface CanvasDatasetBinding {
  id: string;
  snapshotId: string | number;
  rowMode: 'static' | 'template';
  row: number;
  rowSpacing: number;
  maxRows: number | null;
  gridId: string | null;
  slot: string | null;
  roundId: string | null;
}

export type CanvasBindingSource = CanvasDataBinding['source'];
export type CanvasBindingField = CanvasDataBinding['field'];

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
  elementSeries: ElementSeries[]; // New simplified element system
  settings: CanvasSettings;
  backgroundImage?: string | null;
}

export interface SnapLine {
  x?: number;
  y?: number;
}

// Player data for auto-ranking
export interface PlayerData {
  player_name: string;
  total_points: number;
  standing_rank: number;
  player_id?: string;
  discord_id?: string;
  riot_id?: string;
  round_scores?: Record<string, number>;
}
