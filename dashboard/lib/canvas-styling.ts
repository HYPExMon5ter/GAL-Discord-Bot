import type {
  CanvasElement,
  CanvasPropertyType,
  CanvasElementStyle,
  StylePreset,
  UniversalStyleControls,
  ElementTypeStyling,
  PreviewModeConfig,
  PlayerData,
} from '@/types';

// Default universal styling controls
export const DEFAULT_UNIVERSAL_STYLING: UniversalStyleControls = {
  fontSize: 24,
  fontFamily: 'Arial',
  color: '#000000',
  backgroundColor: '#FFFFFF',
  borderColor: '#000000',
  borderWidth: 1,
  borderRadius: 0,
  fontWeight: 'normal',
  textAlign: 'left',
  letterSpacing: 0,
  lineHeight: 1.2,
  textTransform: 'none',
  textShadow: 'none',
  boxShadow: 'none',
  padding: {
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
  },
  margin: {
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
  },
};

// Style presets for common use cases
export const STYLE_PRESETS: StylePreset[] = [
  {
    id: 'player-default',
    name: 'Player Default',
    description: 'Clean player name styling with good contrast',
    style: {
      fontSize: 24,
      fontFamily: 'Arial',
      color: '#FFFFFF',
      backgroundColor: '#3B82F6',
      borderColor: '#1E40AF',
      borderWidth: 2,
      borderRadius: 8,
      fontWeight: 'bold',
      textAlign: 'center',
      letterSpacing: 0,
      lineHeight: 1.2,
      textTransform: 'uppercase',
      textShadow: '1px 1px 2px rgba(0,0,0,0.3)',
      boxShadow: 'none',
      padding: { top: 8, right: 16, bottom: 8, left: 16 },
      margin: { top: 0, right: 0, bottom: 0, left: 0 },
    },
    applicableTo: ['players'],
    category: 'players',
  },
  {
    id: 'score-bold',
    name: 'Score Bold',
    description: 'Prominent score display with strong styling',
    style: {
      fontSize: 32,
      fontFamily: 'Arial Black',
      color: '#FFFFFF',
      backgroundColor: '#EF4444',
      borderColor: '#991B1B',
      borderWidth: 3,
      borderRadius: 12,
      fontWeight: '900',
      textAlign: 'center',
      letterSpacing: 1,
      lineHeight: 1.1,
      textTransform: 'none',
      textShadow: '2px 2px 4px rgba(0,0,0,0.5)',
      boxShadow: 'none',
      padding: { top: 12, right: 20, bottom: 12, left: 20 },
      margin: { top: 0, right: 0, bottom: 0, left: 0 },
    },
    applicableTo: ['scores'],
    category: 'scores',
  },
  {
    id: 'placement-medal',
    name: 'Placement Medal',
    description: 'Elegant placement styling with medal-like appearance',
    style: {
      fontSize: 28,
      fontFamily: 'Georgia',
      color: '#FFD700',
      backgroundColor: '#1F2937',
      borderColor: '#FFD700',
      borderWidth: 4,
      borderRadius: 50,
      fontWeight: 'bold',
      textAlign: 'center',
      letterSpacing: 2,
      lineHeight: 1.1,
      textTransform: 'uppercase',
      textShadow: '0 0 10px rgba(255,215,0,0.5)',
      boxShadow: '0 0 20px rgba(255,215,0,0.3)',
      padding: { top: 16, right: 24, bottom: 16, left: 24 },
      margin: { top: 0, right: 0, bottom: 0, left: 0 },
    },
    applicableTo: ['placement'],
    category: 'placement',
  },
  {
    id: 'minimal-clean',
    name: 'Minimal Clean',
    description: 'Minimalist styling with subtle borders',
    style: {
      fontSize: 20,
      fontFamily: 'Helvetica',
      color: '#374151',
      backgroundColor: 'rgba(255,255,255,0.9)',
      borderColor: '#D1D5DB',
      borderWidth: 1,
      borderRadius: 4,
      fontWeight: 'normal',
      textAlign: 'left',
      letterSpacing: 0,
      lineHeight: 1.4,
      textTransform: 'none',
      textShadow: 'none',
      boxShadow: 'none',
      padding: { top: 6, right: 12, bottom: 6, left: 12 },
      margin: { top: 0, right: 0, bottom: 0, left: 0 },
    },
    applicableTo: ['players', 'scores', 'placement'],
    category: 'universal',
  },
  {
    id: 'esports-pro',
    name: 'Esports Pro',
    description: 'Professional esports styling with high contrast',
    style: {
      fontSize: 26,
      fontFamily: 'Impact',
      color: '#00FF00',
      backgroundColor: '#000000',
      borderColor: '#00FF00',
      borderWidth: 2,
      borderRadius: 0,
      fontWeight: 'normal',
      textAlign: 'center',
      letterSpacing: 2,
      lineHeight: 1.0,
      textTransform: 'uppercase',
      textShadow: '0 0 10px rgba(0,255,0,0.8)',
      boxShadow: '0 0 15px rgba(0,255,0,0.5)',
      padding: { top: 10, right: 18, bottom: 10, left: 18 },
      margin: { top: 0, right: 0, bottom: 0, left: 0 },
    },
    applicableTo: ['players', 'scores', 'placement'],
    category: 'universal',
  },
  {
    id: 'tournament-gold',
    name: 'Tournament Gold',
    description: 'Premium gold styling for tournament elements',
    style: {
      fontSize: 22,
      fontFamily: 'Times New Roman',
      color: '#7C2D12',
      backgroundColor: 'linear-gradient(135deg, #FFD700, #FFA500)',
      borderColor: '#7C2D12',
      borderWidth: 3,
      borderRadius: 15,
      fontWeight: 'bold',
      textAlign: 'center',
      letterSpacing: 1,
      lineHeight: 1.2,
      textTransform: 'capitalize',
      textShadow: '1px 1px 3px rgba(0,0,0,0.3)',
      padding: { top: 12, right: 20, bottom: 12, left: 20 },
      boxShadow: '0 4px 15px rgba(255,215,0,0.4)',
      margin: { top: 0, right: 0, bottom: 0, left: 0 },
    },
    applicableTo: ['players', 'scores', 'placement'],
    category: 'universal',
  },
];

// Font options with display names
export const FONT_OPTIONS = [
  { value: 'Arial', label: 'Arial' },
  { value: 'Arial Black', label: 'Arial Black' },
  { value: 'Times New Roman', label: 'Times New Roman' },
  { value: 'Georgia', label: 'Georgia' },
  { value: 'Helvetica', label: 'Helvetica' },
  { value: 'Verdana', label: 'Verdana' },
  { value: 'Impact', label: 'Impact' },
  { value: 'Trebuchet MS', label: 'Trebuchet MS' },
  { value: 'Courier New', label: 'Courier New' },
];

// Font weight options
export const FONT_WEIGHT_OPTIONS = [
  { value: 'normal', label: 'Normal' },
  { value: 'bold', label: 'Bold' },
  { value: '100', label: 'Thin (100)' },
  { value: '200', label: 'Extra Light (200)' },
  { value: '300', label: 'Light (300)' },
  { value: '400', label: 'Normal (400)' },
  { value: '500', label: 'Medium (500)' },
  { value: '600', label: 'Semi Bold (600)' },
  { value: '700', label: 'Bold (700)' },
  { value: '800', label: 'Extra Bold (800)' },
  { value: '900', label: 'Black (900)' },
];

// Text transform options
export const TEXT_TRANSFORM_OPTIONS = [
  { value: 'none', label: 'None' },
  { value: 'uppercase', label: 'UPPERCASE' },
  { value: 'lowercase', label: 'lowercase' },
  { value: 'capitalize', label: 'Capitalize' },
];

// Text align options
export const TEXT_ALIGN_OPTIONS = [
  { value: 'left', label: 'Left' },
  { value: 'center', label: 'Center' },
  { value: 'right', label: 'Right' },
];

/**
 * Apply universal styling to elements of a specific type
 */
export function applyUniversalStyling(
  elements: CanvasElement[],
  elementType: CanvasPropertyType,
  styling: Partial<UniversalStyleControls>,
): CanvasElement[] {
  return elements.map(element => {
    if (element.type === elementType) {
      return {
        ...element,
        ...styling,
      };
    }
    return element;
  });
}

/**
 * Apply style preset to elements of specific types
 */
export function applyStylePreset(
  elements: CanvasElement[],
  preset: StylePreset,
): CanvasElement[] {
  return elements.map(element => {
    if (preset.applicableTo.includes(element.type as CanvasPropertyType)) {
      return {
        ...element,
        ...preset.style,
      };
    }
    return element;
  });
}

/**
 * Get applicable presets for an element type
 */
export function getApplicablePresets(elementType: CanvasPropertyType): StylePreset[] {
  return STYLE_PRESETS.filter(preset => 
    preset.applicableTo.includes(elementType) || preset.category === 'universal'
  );
}

/**
 * Get preset by ID
 */
export function getPresetById(id: string): StylePreset | undefined {
  return STYLE_PRESETS.find(preset => preset.id === id);
}

/**
 * Create element type styling configuration
 */
export function createElementTypeStyling(
  elementType: CanvasPropertyType,
  universalStyle: Partial<UniversalStyleControls> = {},
  overrides: CanvasElementStyle = {},
  presetId?: string,
): ElementTypeStyling {
  return {
    elementType,
    universalStyle,
    overrides,
    presetId,
  };
}

/**
 * Apply element type styling to elements
 */
export function applyElementTypeStyling(
  elements: CanvasElement[],
  styling: ElementTypeStyling,
): CanvasElement[] {
  return elements.map(element => {
    if (element.type === styling.elementType) {
      let updatedElement = { ...element };

      // Apply universal styling
      updatedElement = { ...updatedElement, ...styling.universalStyle };

      // Apply preset if specified
      if (styling.presetId) {
        const preset = getPresetById(styling.presetId);
        if (preset) {
          updatedElement = { ...updatedElement, ...preset.style };
        }
      }

      // Apply overrides (these take precedence)
      updatedElement = { ...updatedElement, ...styling.overrides };

      return updatedElement;
    }
    return element;
  });
}

/**
 * Generate mock player data for preview mode
 */
export function generateMockPlayerData(count: number = 10): PlayerData[] {
  const firstNames = ['Alex', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Jamie', 'Avery', 'Quinn', 'Sage'];
  const lastNames = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez'];
  const teams = ['Thunder', 'Lightning', 'Phoenix', 'Dragons', 'Titans', 'Vikings', 'Rangers', 'Warriors'];

  const mockData: PlayerData[] = [];
  
  for (let i = 0; i < count; i++) {
    const firstName = firstNames[i % firstNames.length];
    const lastName = lastNames[Math.floor(i / firstNames.length) % lastNames.length];
    const team = teams[i % teams.length];
    
    mockData.push({
      player_name: `${firstName} "${team}" ${lastName}`,
      total_points: Math.max(0, 1000 - (i * 85) + Math.floor(Math.random() * 50)),
      standing_rank: i + 1,
      player_id: `player_${i + 1}`,
      discord_id: `discord_${i + 1}`,
      riot_id: `riot_${i + 1}`,
      round_scores: {
        round_1: Math.floor(Math.random() * 300),
        round_2: Math.floor(Math.random() * 300),
        round_3: Math.floor(Math.random() * 300),
      },
    });
  }

  return mockData;
}

/**
 * Get default preview mode configuration
 */
export function getDefaultPreviewModeConfig(): PreviewModeConfig {
  return {
    enabled: false,
    mockData: true,
    showPlacementPositions: true,
    liveUpdates: true,
    playerCount: 10,
    sortBy: 'total_points',
    sortOrder: 'desc',
  };
}

/**
 * Convert element style to CSS style string
 */
export function elementStyleToCss(style: CanvasElementStyle): React.CSSProperties {
  const css: React.CSSProperties = {};

  if (style.fontSize) css.fontSize = `${style.fontSize}px`;
  if (style.fontFamily) css.fontFamily = style.fontFamily;
  if (style.color) css.color = style.color;

  return css;
}

/**
 * Validate style values and return cleaned version
 */
export function validateAndCleanStyle(style: Partial<CanvasElementStyle>): Partial<CanvasElementStyle> {
  const cleaned: Partial<CanvasElementStyle> = {};

  // Validate numeric values
  if (style.fontSize !== undefined && style.fontSize > 0 && style.fontSize <= 1000) {
    cleaned.fontSize = style.fontSize;
  }

  

  // Validate string values
  if (style.fontFamily && typeof style.fontFamily === 'string' && style.fontFamily.trim()) {
    cleaned.fontFamily = style.fontFamily.trim();
  }

  if (style.color && typeof style.color === 'string' && /^#[0-9A-Fa-f]{6}$/.test(style.color)) {
    cleaned.color = style.color;
  }

  

  

  return cleaned;
}
