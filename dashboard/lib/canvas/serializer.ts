import type { CanvasState, CanvasElement } from '@/lib/canvas/types';

// Simple serialize/deserialize for save/load
// No legacy conversion needed - clean start

export function serializeCanvasState(state: CanvasState): string {
  return JSON.stringify(state);
}

export function deserializeCanvasState(json: string | object): CanvasState {
  try {
    if (typeof json === 'string') {
      return JSON.parse(json);
    }
    
    if (typeof json === 'object' && json !== null) {
      return json as CanvasState;
    }
    
    return { background: null, elements: [] };
  } catch (error) {
    console.error('Failed to deserialize canvas state:', error);
    return { background: null, elements: [] };
  }
}

// Validate canvas state
export function validateCanvasState(state: CanvasState): boolean {
  if (!state || typeof state !== 'object') return false;
  
  if (state.background && (!state.background.imageUrl || !state.background.width || !state.background.height)) {
    return false;
  }
  
  if (!Array.isArray(state.elements)) return false;
  
  // Basic element validation
  for (const element of state.elements) {
    if (!element.id || !element.type || typeof element.x !== 'number' || typeof element.y !== 'number') {
      return false;
    }
    
    if (element.type === 'text' && !('content' in element)) {
      return false;
    }
    
    if (element.type !== 'text' && (!('spacing' in element || !('previewCount' in element))) {
      return false;
    }
  }
  
  return true;
}

// Migration helper for new elements (no legacy conversion)
export function migrateElement(element: any): CanvasElement | null {
  if (!element || typeof element !== 'object') return null;
  
  // Basic validation
  if (!element.id || !element.type || typeof element.x !== 'number' || typeof element.y !== 'number') {
    return null;
  }
  
  // Type validation
  const validTypes = ['text', 'players', 'scores', 'placements'];
  if (!validTypes.includes(element.type)) {
    return null;
  }
  
  // Return cleaned element
  return element as CanvasElement;
}
