import type {
  CanvasElement,
  CanvasPropertyType,
  CanvasSettings,
  CanvasState,
  SnapLine,
  ElementSeries,
  ElementSpacing,
  PlayerData,
  CanvasDataBinding,
  PreviewModeConfig,
  UniversalStyleControls,
} from '@/types';

export const DEFAULT_CANVAS_SETTINGS: CanvasSettings = {
  width: 5000,
  height: 5000,
  backgroundColor: '#2a2a2a',
};

const DEFAULT_TEXT_DIMENSIONS = { width: 100, height: 50 };
const DEFAULT_BLOCK_DIMENSIONS = { width: 100, height: 50 };

const PROPERTY_CONFIG: Record<
  CanvasPropertyType,
  { placeholder: string; width: number; height: number }
> = {
  players: { placeholder: 'Player Name', width: 150, height: 40 },
  scores: { placeholder: 'Score', width: 100, height: 40 },
  placement: { placeholder: 'Placement', width: 120, height: 40 },
};

export const DEFAULT_ELEMENT_SPACING: ElementSpacing = {
  horizontal: 20,
  vertical: 60,
  direction: 'vertical',
};

export function generateElementId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `element-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

export function normalizeCanvasElement(element: any): CanvasElement {
  const type = (element?.type ?? 'text') as CanvasElement['type'];
  return {
    id: typeof element?.id === 'string' ? element.id : generateElementId(),
    type,
    content: typeof element?.content === 'string' ? element.content : undefined,
    placeholderText:
      typeof element?.placeholderText === 'string' ? element.placeholderText : undefined,
    x: toNumberWithDefault(element?.x, 0),
    y: toNumberWithDefault(element?.y, 0),
    width: element?.width != null ? toOptionalNumber(element.width) : undefined,
    height: element?.height != null ? toOptionalNumber(element.height) : undefined,
    fontSize: element?.fontSize != null ? toOptionalNumber(element.fontSize) : undefined,
    fontFamily:
      typeof element?.fontFamily === 'string' ? element.fontFamily : undefined,
    color: typeof element?.color === 'string' ? element.color : undefined,
    backgroundColor:
      typeof element?.backgroundColor === 'string' ? element.backgroundColor : undefined,
    borderColor:
      typeof element?.borderColor === 'string' ? element.borderColor : undefined,
    borderWidth:
      element?.borderWidth != null ? toOptionalNumber(element.borderWidth) : undefined,
    borderRadius:
      element?.borderRadius != null ? toOptionalNumber(element.borderRadius) : undefined,
    fontWeight: typeof element?.fontWeight === 'string' ? element.fontWeight : undefined,
    textAlign: (element?.textAlign === 'left' || element?.textAlign === 'center' || element?.textAlign === 'right')
      ? element.textAlign
      : undefined,
    letterSpacing: element?.letterSpacing != null ? toOptionalNumber(element.letterSpacing) : undefined,
    lineHeight: element?.lineHeight != null ? toOptionalNumber(element.lineHeight) : undefined,
    textTransform: (element?.textTransform === 'none' || element?.textTransform === 'uppercase' || 
                    element?.textTransform === 'lowercase' || element?.textTransform === 'capitalize')
      ? element.textTransform
      : undefined,
    textShadow: typeof element?.textShadow === 'string' ? element.textShadow : undefined,
    boxShadow: typeof element?.boxShadow === 'string' ? element.boxShadow : undefined,
    padding: element?.padding && typeof element.padding === 'object' ? {
      top: element.padding.top != null ? toOptionalNumber(element.padding.top) : undefined,
      right: element.padding.right != null ? toOptionalNumber(element.padding.right) : undefined,
      bottom: element.padding.bottom != null ? toOptionalNumber(element.padding.bottom) : undefined,
      left: element.padding.left != null ? toOptionalNumber(element.padding.left) : undefined,
    } : undefined,
    margin: element?.margin && typeof element.margin === 'object' ? {
      top: element.margin.top != null ? toOptionalNumber(element.margin.top) : undefined,
      right: element.margin.right != null ? toOptionalNumber(element.margin.right) : undefined,
      bottom: element.margin.bottom != null ? toOptionalNumber(element.margin.bottom) : undefined,
      left: element.margin.left != null ? toOptionalNumber(element.margin.left) : undefined,
    } : undefined,
    dataBinding: normalizeDataBinding(element?.dataBinding),
    isPlaceholder: Boolean(element?.isPlaceholder),
  };
}

function normalizeDataBinding(binding: any): CanvasElement['dataBinding'] {
  if (!binding) return null;
  if (typeof binding !== 'object') return null;
  const field = binding.field;
  if (
    field !== 'player_name' &&
    field !== 'player_score' &&
    field !== 'player_placement' &&
    field !== 'player_rank' &&
    field !== 'team_name' &&
    field !== 'round_score'
  ) {
    return null;
  }
  const source = (binding.source === 'manual' || binding.source === 'series' || binding.source === 'dataset') 
    ? binding.source 
    : 'api';
  return {
    source,
    field,
    apiEndpoint:
      typeof binding.apiEndpoint === 'string' || binding.apiEndpoint === null
        ? binding.apiEndpoint
        : undefined,
    manualValue:
      typeof binding.manualValue === 'string' || binding.manualValue === null
        ? binding.manualValue
        : undefined,
    seriesId:
      typeof binding.seriesId === 'string' || binding.seriesId === null
        ? binding.seriesId
        : undefined,
    fallbackText:
      typeof binding.fallbackText === 'string' || binding.fallbackText === null
        ? binding.fallbackText
        : undefined,
    dataset: binding.dataset || undefined,
  };
}

export function deserializeCanvasState(raw: unknown): CanvasState {
  const parsed =
    typeof raw === 'string'
      ? safeJsonParse(raw)
      : typeof raw === 'object'
      ? raw
      : undefined;

  return normalizeCanvasState(parsed);
}

function safeJsonParse(value: string): unknown {
  try {
    return JSON.parse(value);
  } catch {
    return undefined;
  }
}

function normalizeCanvasState(value: any): CanvasState {
  const elements: CanvasElement[] = Array.isArray(value?.elements)
    ? value.elements.map(normalizeCanvasElement)
    : [];

  const elementSeries: ElementSeries[] = Array.isArray(value?.elementSeries)
    ? value.elementSeries.map(normalizeElementSeries)
    : [];

  const settings = value?.settings ?? {};
  return {
    elements,
    elementSeries,
    settings: {
      width: toNumberWithDefault(settings.width, DEFAULT_CANVAS_SETTINGS.width),
      height: toNumberWithDefault(settings.height, DEFAULT_CANVAS_SETTINGS.height),
      backgroundColor:
        typeof settings.backgroundColor === 'string'
          ? settings.backgroundColor
          : DEFAULT_CANVAS_SETTINGS.backgroundColor,
    },
    backgroundImage:
      typeof value?.backgroundImage === 'string' ? value.backgroundImage : null,
    previewConfig: value?.previewConfig || {
      enabled: false,
      mockData: true,
      showPlacementPositions: true,
      liveUpdates: true,
      playerCount: 10,
      sortBy: 'total_points',
      sortOrder: 'desc',
    },
  };
}

function toNumberWithDefault(value: any, fallback: number): number {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : fallback;
}

function toOptionalNumber(value: any): number | undefined {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : undefined;
}

export function createTextElement(snap: (value: number) => number): CanvasElement {
  return {
    id: generateElementId(),
    type: 'text',
    content: 'Text',
    x: snap(100),
    y: snap(100),
    fontSize: 48,
    fontFamily: 'Arial',
    color: '#000000',
  };
}

export function createPropertyElement(
  type: CanvasPropertyType,
  snap: (value: number) => number,
): CanvasElement {
  const config = PROPERTY_CONFIG[type];
  return {
    id: generateElementId(),
    type,
    content: config.placeholder,
    placeholderText: config.placeholder,
    x: snap(100),
    y: snap(100),
    width: snap(config.width),
    height: snap(config.height),
    fontSize: 24,
    fontFamily: 'Arial',
    color: '#000000',
    backgroundColor: '#3B82F6',
    dataBinding: {
      source: 'api',
      field:
        type === 'players'
          ? 'player_name'
          : type === 'scores'
          ? 'player_score'
          : 'player_placement',
      apiEndpoint: null,
      manualValue: null,
    },
    isPlaceholder: true,
  };
}

export function snapValueToGrid(
  value: number,
  gridSize: number,
  enabled: boolean,
): number {
  if (!enabled) return value;
  return Math.round(value / gridSize) * gridSize;
}

export interface UpdateCanvasElementOptions {
  gridSize: number;
  gridSnapEnabled: boolean;
}

export function updateCanvasElement(
  elements: CanvasElement[],
  elementId: string,
  updates: Partial<CanvasElement>,
  options: UpdateCanvasElementOptions,
): { updatedElements: CanvasElement[]; previous: CanvasElement; next: CanvasElement } | null {
  const index = elements.findIndex((element) => element.id === elementId);
  if (index === -1) return null;

  const previous = elements[index];
  const snappedUpdates: Partial<CanvasElement> = { ...updates };

  if (updates.x != null) {
    snappedUpdates.x = snapValueToGrid(updates.x, options.gridSize, options.gridSnapEnabled);
  }
  if (updates.y != null) {
    snappedUpdates.y = snapValueToGrid(updates.y, options.gridSize, options.gridSnapEnabled);
  }
  if (updates.width != null) {
    snappedUpdates.width = snapValueToGrid(
      updates.width,
      options.gridSize,
      options.gridSnapEnabled,
    );
  }
  if (updates.height != null) {
    snappedUpdates.height = snapValueToGrid(
      updates.height,
      options.gridSize,
      options.gridSnapEnabled,
    );
  }

  const next: CanvasElement = normalizeCanvasElement({
    ...previous,
    ...snappedUpdates,
  });

  const updatedElements = [...elements];
  updatedElements[index] = next;

  return { updatedElements, previous, next };
}

export function removeCanvasElement(
  elements: CanvasElement[],
  elementId: string,
): { updatedElements: CanvasElement[]; removed: CanvasElement | null } {
  const index = elements.findIndex((element) => element.id === elementId);
  if (index === -1) {
    return { updatedElements: elements, removed: null };
  }

  const updatedElements = elements.slice(0, index).concat(elements.slice(index + 1));
  return { updatedElements, removed: elements[index] };
}

export function clampPositionToCanvas(
  position: { x: number; y: number },
  element: CanvasElement,
  settings: CanvasSettings,
): { x: number; y: number } {
  const { width, height } = getElementDimensions(element);

  const clampedX = Math.max(0, Math.min(position.x, settings.width - width));
  const clampedY = Math.max(0, Math.min(position.y, settings.height - height));

  return { x: clampedX, y: clampedY };
}

function getElementDimensions(element: CanvasElement): { width: number; height: number } {
  if (element.width != null && element.height != null) {
    return { width: element.width, height: element.height };
  }

  if (element.type === 'text') {
    return { ...DEFAULT_TEXT_DIMENSIONS };
  }

  return { ...DEFAULT_BLOCK_DIMENSIONS };
}

export function calculateSnapAgainstElements(options: {
  element: CanvasElement;
  elements: CanvasElement[];
  position: { x: number; y: number };
  snapToElements: boolean;
  gridSize: number;
}): { position: { x: number; y: number }; lines: SnapLine[] } {
  const { element, elements, position, snapToElements, gridSize } = options;

  if (!snapToElements) {
    return { position, lines: [] };
  }

  const { width: elementWidth, height: elementHeight } = getElementDimensions(element);
  let snappedX = position.x;
  let snappedY = position.y;
  const snapThreshold = gridSize;
  const lines: SnapLine[] = [];

  elements.forEach((other) => {
    if (other.id === element.id) return;

    const { width: otherWidth, height: otherHeight } = getElementDimensions(other);

    const otherLeft = other.x;
    const otherRight = other.x + otherWidth;
    const otherTop = other.y;
    const otherBottom = other.y + otherHeight;

    const elemLeft = position.x;
    const elemRight = position.x + elementWidth;
    const elemTop = position.y;
    const elemBottom = position.y + elementHeight;

    if (Math.abs(elemLeft - otherLeft) < snapThreshold) {
      snappedX = otherLeft;
      lines.push({ x: otherLeft });
    }
    if (Math.abs(elemLeft - otherRight) < snapThreshold) {
      snappedX = otherRight;
      lines.push({ x: otherRight });
    }
    if (Math.abs(elemRight - otherLeft) < snapThreshold) {
      snappedX = otherLeft - elementWidth;
      lines.push({ x: otherLeft });
    }
    if (Math.abs(elemRight - otherRight) < snapThreshold) {
      snappedX = otherRight - elementWidth;
      lines.push({ x: otherRight });
    }

    if (Math.abs(elemTop - otherTop) < snapThreshold) {
      snappedY = otherTop;
      lines.push({ y: otherTop });
    }
    if (Math.abs(elemTop - otherBottom) < snapThreshold) {
      snappedY = otherBottom;
      lines.push({ y: otherBottom });
    }
    if (Math.abs(elemBottom - otherTop) < snapThreshold) {
      snappedY = otherTop - elementHeight;
      lines.push({ y: otherTop });
    }
    if (Math.abs(elemBottom - otherBottom) < snapThreshold) {
      snappedY = otherBottom - elementHeight;
      lines.push({ y: otherBottom });
    }

    const otherCenterX = otherLeft + otherWidth / 2;
    const otherCenterY = otherTop + otherHeight / 2;
    const elemCenterX = elemLeft + elementWidth / 2;
    const elemCenterY = elemTop + elementHeight / 2;

    if (Math.abs(elemCenterX - otherCenterX) < snapThreshold) {
      snappedX = otherCenterX - elementWidth / 2;
      lines.push({ x: otherCenterX });
    }
    if (Math.abs(elemCenterY - otherCenterY) < snapThreshold) {
      snappedY = otherCenterY - elementHeight / 2;
      lines.push({ y: otherCenterY });
    }
  });

  return { position: { x: snappedX, y: snappedY }, lines };
}

// Element Series Functions for Simplified Canvas System

function normalizeElementSeries(series: any): ElementSeries {
  return {
    id: typeof series?.id === 'string' ? series.id : generateElementId(),
    type: series?.type === 'players' || series?.type === 'scores' || series?.type === 'placement' 
      ? series.type 
      : 'players',
    baseElement: normalizeCanvasElement(series?.baseElement),
    spacing: normalizeElementSpacing(series?.spacing),
    autoGenerate: Boolean(series?.autoGenerate),
    maxElements: series?.maxElements != null ? toOptionalNumber(series.maxElements) : undefined,
    sortBy: series?.sortBy === 'total_points' || series?.sortBy === 'player_name' || series?.sortBy === 'standing_rank'
      ? series.sortBy 
      : 'total_points',
    sortOrder: series?.sortOrder === 'asc' || series?.sortOrder === 'desc' 
      ? series.sortOrder 
      : 'desc',
  };
}

function normalizeElementSpacing(spacing: any): ElementSpacing {
  return {
    horizontal: toNumberWithDefault(spacing?.horizontal, DEFAULT_ELEMENT_SPACING.horizontal),
    vertical: toNumberWithDefault(spacing?.vertical, DEFAULT_ELEMENT_SPACING.vertical),
    direction: spacing?.direction === 'horizontal' || spacing?.direction === 'vertical' || spacing?.direction === 'grid'
      ? spacing.direction
      : DEFAULT_ELEMENT_SPACING.direction,
  };
}

export function generateElementSeriesId(): string {
  return `series-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

export function createElementSeries(
  type: CanvasPropertyType,
  baseElement: CanvasElement,
  spacing: ElementSpacing = DEFAULT_ELEMENT_SPACING,
): ElementSeries {
  return {
    id: generateElementSeriesId(),
    type,
    baseElement,
    spacing,
    autoGenerate: true,
    sortBy: 'total_points',
    sortOrder: 'desc',
  };
}

export function generateElementsFromSeries(
  series: ElementSeries,
  playerData: PlayerData[],
): CanvasElement[] {
  if (!series.autoGenerate || !playerData.length) {
    return [series.baseElement];
  }

  // Sort player data based on series configuration
  const sortedData = [...playerData].sort((a, b) => {
    let comparison = 0;
    
    switch (series.sortBy) {
      case 'total_points':
        comparison = a.total_points - b.total_points;
        break;
      case 'player_name':
        comparison = a.player_name.localeCompare(b.player_name);
        break;
      case 'standing_rank':
        comparison = a.standing_rank - b.standing_rank;
        break;
    }
    
    return series.sortOrder === 'asc' ? comparison : -comparison;
  });

  // Apply max elements limit if specified
  const limitedData = series.maxElements 
    ? sortedData.slice(0, series.maxElements)
    : sortedData;

  // Generate elements based on spacing configuration
  const elements: CanvasElement[] = [];
  
  limitedData.forEach((player, index) => {
    const element = {
      ...series.baseElement,
      id: `${series.id}-element-${index}`,
      x: calculateElementPosition(series.baseElement.x, series.spacing.horizontal, index, series.spacing.direction === 'horizontal'),
      y: calculateElementPosition(series.baseElement.y, series.spacing.vertical, index, series.spacing.direction === 'vertical'),
      dataBinding: {
        source: 'series' as const,
        field: getBindingFieldForElementType(series.type),
        seriesId: series.id,
        manualValue: getElementValueForPlayer(player, series.type, series.roundId),
      },
      isPlaceholder: false,
    };
    
    elements.push(element);
  });

  return elements;
}

function calculateElementPosition(basePosition: number, spacing: number, index: number, isPrimaryDirection: boolean): number {
  if (!isPrimaryDirection && index > 0) {
    // For grid layout, secondary direction uses a different calculation
    const gridColumns = 5; // Default grid columns
    const row = Math.floor(index / gridColumns);
    return basePosition + (row * spacing);
  }
  return basePosition + (index * spacing);
}

function getBindingFieldForElementType(type: CanvasPropertyType): CanvasDataBinding['field'] {
  switch (type) {
    case 'players':
      return 'player_name';
    case 'scores':
      return 'player_score';
    case 'placement':
      return 'player_placement';
    default:
      return 'player_name';
  }
}

function getElementValueForPlayer(player: PlayerData, type: CanvasPropertyType, roundId?: string): string {
  switch (type) {
    case 'players':
      return player.player_name;
    case 'scores':
      if (roundId && player.round_scores && player.round_scores[roundId]) {
        return player.round_scores[roundId].toString();
      }
      return player.total_points.toString();
    case 'placement':
      return player.standing_rank.toString();
    default:
      return player.player_name;
  }
}

export function updateElementSeries(
  elementSeries: ElementSeries[],
  seriesId: string,
  updates: Partial<ElementSeries>,
): ElementSeries[] {
  return elementSeries.map(series => 
    series.id === seriesId 
      ? { ...series, ...updates }
      : series
  );
}

export function deleteElementSeries(
  elementSeries: ElementSeries[],
  seriesId: string,
): { updatedSeries: ElementSeries[]; removed: ElementSeries | null } {
  const index = elementSeries.findIndex(series => series.id === seriesId);
  if (index === -1) {
    return { updatedSeries: elementSeries, removed: null };
  }

  const updatedSeries = elementSeries.slice(0, index).concat(elementSeries.slice(index + 1));
  return { updatedSeries, removed: elementSeries[index] };
}

export function serializeCanvasState(state: CanvasState): string {
  const normalized = normalizeCanvasState({
    elements: state.elements,
    elementSeries: state.elementSeries,
    settings: state.settings,
    backgroundImage: state.backgroundImage ?? null,
    previewConfig: state.previewConfig,
  });

  return JSON.stringify(normalized);
}

export function updateCanvasBackground(
  state: CanvasState,
  backgroundImage: string | null,
  dimensions?: { width: number; height: number },
): CanvasState {
  return {
    elements: state.elements,
    elementSeries: state.elementSeries,
    backgroundImage,
    settings: {
      width: dimensions?.width ?? state.settings.width,
      height: dimensions?.height ?? state.settings.height,
      backgroundColor: state.settings.backgroundColor,
    },
  };
}

export function updateCanvasSettings(
  state: CanvasState,
  settings: Partial<CanvasSettings>,
): CanvasState {
  return {
    ...state,
    elementSeries: state.elementSeries,
    settings: {
      width: settings.width ?? state.settings.width,
      height: settings.height ?? state.settings.height,
      backgroundColor: settings.backgroundColor ?? state.settings.backgroundColor,
    },
  };
}

// Styling system functions

/**
 * Apply universal styling to all elements of a specific type
 */
export function applyUniversalStylingToElements(
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
 * Update preview mode configuration in canvas state
 */
export function updatePreviewModeConfig(
  state: CanvasState,
  previewConfig: Partial<PreviewModeConfig>,
): CanvasState {
  return {
    ...state,
    previewConfig: {
      enabled: previewConfig.enabled ?? false,
      mockData: previewConfig.mockData ?? true,
      showPlacementPositions: previewConfig.showPlacementPositions ?? true,
      liveUpdates: previewConfig.liveUpdates ?? true,
      playerCount: previewConfig.playerCount ?? 10,
      sortBy: previewConfig.sortBy ?? 'total_points',
      sortOrder: previewConfig.sortOrder ?? 'desc',
    },
  };
}

/**
 * Get elements with preview data applied
 */
export function getElementsWithPreviewData(
  elements: CanvasElement[],
  elementSeries: ElementSeries[],
  previewConfig: PreviewModeConfig,
): CanvasElement[] {
  if (!previewConfig.enabled) {
    return elements;
  }

  // If preview is enabled, generate elements from series with mock data
  const previewElements: CanvasElement[] = [];
  
  // Add non-series elements first
  elements.forEach(element => {
    if (!element.dataBinding?.seriesId) {
      previewElements.push(element);
    }
  });

  // Add elements from series with mock data
  elementSeries.forEach(series => {
    const mockData = generateMockPlayerData(previewConfig.playerCount || 10);
    const seriesElements = generateElementsFromSeries(series, mockData);
    previewElements.push(...seriesElements);
  });

  return previewElements;
}

/**
 * Generate mock player data for preview
 */
function generateMockPlayerData(count: number = 10): PlayerData[] {
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
