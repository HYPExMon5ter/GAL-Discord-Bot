// Canvas System - Clean Type Definitions
// No legacy complexity - simple, maintainable types

export interface CanvasState {
  background: BackgroundConfig | null;
  elements: CanvasElement[];
}

export interface BackgroundConfig {
  imageUrl: string;      // base64 or URL
  width: number;         // pixels
  height: number;        // pixels
}

export type ElementType = 'text' | 'players' | 'scores' | 'placements';

export interface BaseElement {
  id: string;
  type: ElementType;
  x: number;
  y: number;
  fontSize: number;
  fontFamily: string;
  color: string;
}

export interface TextElement extends BaseElement {
  type: 'text';
  content: string;
}

export interface DynamicElement extends BaseElement {
  type: 'players' | 'scores' | 'placements';
  spacing: number;           // Vertical spacing (default: 56px)
  previewCount: number;      // Mock items in editor (8-16)
  roundId?: string;          // For scores: 'total' | 'round_1' | 'round_2' etc.
}

export type CanvasElement = TextElement | DynamicElement;

// View mode only - real tournament data
export interface PlayerData {
  player_name: string;
  total_points: number;
  standing_rank: number;
  round_scores?: Record<string, number>;
}

// Element creation helpers
export interface ElementDefaults {
  fontSize: number;
  fontFamily: string;
  color: string;
  x: number;
  y: number;
}

export const DEFAULT_ELEMENT_CONFIGS: Record<ElementType, ElementDefaults> = {
  text: {
    fontSize: 24,
    fontFamily: 'Arial',
    color: '#000000',
    x: 100,
    y: 100
  },
  players: {
    fontSize: 20,
    fontFamily: 'Arial',
    color: '#FFFFFF',
    x: 100,
    y: 200
  },
  scores: {
    fontSize: 24,
    fontFamily: 'Arial',
    color: '#FFFFFF',
    x: 400,
    y: 200
  },
  placements: {
    fontSize: 20,
    fontFamily: 'Arial',
    color: '#FFD700',
    x: 600,
    y: 200
  }
};

export const DEFAULT_PREVIEW_COUNT = 10;
export const DEFAULT_SPACING = 56;
