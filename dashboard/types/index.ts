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

// Simplified element types - unified system
export type ElementType = 'text' | 'player_name' | 'player_score' | 'player_placement' | 'team_name' | 'round_score';

// For backward compatibility
export type CanvasElementType = ElementType;
export type CanvasPropertyType = Extract<ElementType, 'player_name' | 'player_score' | 'player_placement' | 'team_name' | 'round_score'>;

// Simplified element series for auto-generation
export interface ElementSeries {
  id: string;
  type: CanvasPropertyType;
  baseElement: CanvasElement; // The first placed element
  spacing: ElementSpacing;
  autoGenerate: boolean;
  maxElements?: number;
  sortBy: 'total_points' | 'player_name' | 'standing_rank';
  sortOrder: 'asc' | 'desc';
  roundId?: string; // For round-specific scoring
}

export interface ElementSpacing {
  horizontal: number;
  vertical: number;
  direction: 'horizontal' | 'vertical' | 'grid';
}

// Simplified data binding - just Static vs Dynamic
export interface ElementDataBinding {
  source: 'static' | 'dynamic';
  dataType?: ElementType; // For dynamic elements, what data to bind
  staticValue?: string; // For static elements, the text content
  snapshotId?: string | number; // For dynamic elements, which snapshot to use
  roundId?: string; // For round-specific data
  fallbackText?: string; // Shown when data is unavailable
  seriesId?: string | null; // For series-generated elements
}

// For backward compatibility
export interface CanvasDataBinding {
  source: 'api' | 'manual' | 'series' | 'static' | 'dynamic';
  field: 'player_name' | 'player_score' | 'player_placement' | 'player_rank' | 'team_name' | 'round_score';
  apiEndpoint?: string | null;
  manualValue?: string | null;
  seriesId?: string | null;
  fallbackText?: string | null;
  // New simplified fields
  dataType?: ElementType;
  staticValue?: string;
  snapshotId?: string | number;
  roundId?: string;
}

export type CanvasBindingSource = CanvasDataBinding['source'];
export type CanvasBindingField = CanvasDataBinding['field'];

export interface CanvasElementStyle {
  fontSize?: number;
  fontFamily?: string;
  color?: string;
  spacing?: number; // For dynamic elements (players, scores, placement)
  lineHeight?: number;
  textTransform?: 'none' | 'uppercase' | 'lowercase' | 'capitalize';
  textShadow?: string;
  boxShadow?: string;
  padding?: {
    top?: number;
    right?: number;
    bottom?: number;
    left?: number;
  };
  margin?: {
    top?: number;
    right?: number;
    bottom?: number;
    left?: number;
  };
}

// Unified element interface
export interface CanvasElement extends CanvasElementStyle {
  id: string;
  type: CanvasElementType;
  content?: string; // For static elements
  placeholderText?: string;
  x: number;
  y: number;
  width?: number;
  height?: number;
  dataBinding?: CanvasDataBinding | ElementDataBinding | null;
  isPlaceholder?: boolean;
  // New simplified properties
  dataSource?: 'static' | 'dynamic'; // Quick reference for binding source
  dataType?: ElementType; // What type of data this element represents
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
  previewConfig?: PreviewModeConfig;
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

// Simplified style presets for element types
export interface StylePreset {
  id: string;
  name: string;
  description: string;
  style: CanvasElementStyle;
  applicableTo: CanvasPropertyType[];
  category: 'text' | 'players' | 'scores' | 'placement' | 'universal';
}

// Simplified universal styling controls
export interface UniversalStyleControls {
  fontSize: number;
  fontFamily: string;
  color: string;
  backgroundColor: string;
  borderColor: string;
  borderWidth: number;
  borderRadius: number;
  fontWeight: string;
  textAlign: 'left' | 'center' | 'right';
  letterSpacing: number;
  lineHeight: number;
  textTransform: 'none' | 'uppercase' | 'lowercase' | 'capitalize';
  textShadow: string;
  boxShadow: string;
  padding: {
    top: number;
    right: number;
    bottom: number;
    left: number;
  };
  margin: {
    top: number;
    right: number;
    bottom: number;
    left: number;
  };
}

// Preview mode configuration
export interface PreviewModeConfig {
  enabled: boolean;
  mockData: boolean;
  showPlacementPositions: boolean;
  liveUpdates: boolean;
  playerCount?: number;
  sortBy: 'total_points' | 'player_name' | 'standing_rank';
  sortOrder: 'asc' | 'desc';
}

// Element type styling configuration
export interface ElementTypeStyling {
  elementType: CanvasPropertyType;
  universalStyle: Partial<UniversalStyleControls>;
  overrides: CanvasElementStyle;
  presetId?: string;
}

// Helper types for simplified system
export interface ElementConfig {
  type: ElementType;
  label: string;
  icon: string; // Icon name for UI
  category: 'static' | 'dynamic';
  description: string;
  defaultStyle?: Partial<CanvasElementStyle>;
}

export const ELEMENT_CONFIGS: Record<ElementType, ElementConfig> = {
  text: {
    type: 'text',
    label: 'Static Text',
    icon: 'Type',
    category: 'static',
    description: 'Static text that doesn\'t change',
    defaultStyle: {
      fontSize: 24,
      fontFamily: 'Arial',
      color: '#000000',
    }
  },
  player_name: {
    type: 'player_name',
    label: 'Player Name',
    icon: 'User',
    category: 'dynamic',
    description: 'Player name from tournament data',
    defaultStyle: {
      fontSize: 20,
      fontFamily: 'Arial',
      color: '#FFFFFF',
      backgroundColor: '#3B82F6',
    }
  },
  player_score: {
    type: 'player_score',
    label: 'Player Score',
    icon: 'Trophy',
    category: 'dynamic',
    description: 'Player total points from tournament data',
    defaultStyle: {
      fontSize: 24,
      fontFamily: 'Arial',
      color: '#FFFFFF',
      backgroundColor: '#EF4444',
    }
  },
  player_placement: {
    type: 'player_placement',
    label: 'Player Placement',
    icon: 'Medal',
    category: 'dynamic',
    description: 'Player standing/rank from tournament data',
    defaultStyle: {
      fontSize: 20,
      fontFamily: 'Arial',
      color: '#FFD700',
      backgroundColor: '#1F2937',
    }
  },
  team_name: {
    type: 'team_name',
    label: 'Team Name',
    icon: 'Users',
    category: 'dynamic',
    description: 'Team name from tournament data',
    defaultStyle: {
      fontSize: 18,
      fontFamily: 'Arial',
      color: '#FFFFFF',
      backgroundColor: '#10B981',
    }
  },
  round_score: {
    type: 'round_score',
    label: 'Round Score',
    icon: 'Target',
    category: 'dynamic',
    description: 'Score from a specific round',
    defaultStyle: {
      fontSize: 16,
      fontFamily: 'Arial',
      color: '#FFFFFF',
      backgroundColor: '#F59E0B',
    }
  }
};
