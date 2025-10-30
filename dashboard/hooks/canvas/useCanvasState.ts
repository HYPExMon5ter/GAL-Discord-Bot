import { useState, useCallback, useEffect } from 'react';
import type { CanvasState, CanvasElement, BackgroundConfig } from '@/lib/canvas/types';
import { serializeCanvasState, deserializeCanvasState } from '@/lib/canvas/serializer';
import { createTextElement, createDynamicElement } from '@/lib/canvas/element-factory';
import { useUndoRedo } from './useUndoRedo';

export function useCanvasState(initialJson?: string) {
  const [canvas, setCanvas] = useState<CanvasState>(() => {
    if (initialJson) {
      try {
        return deserializeCanvasState(initialJson);
      } catch (error) {
        console.error('Failed to parse initial canvas state:', error);
      }
    }
    return { background: null, elements: [] };
  });

  // Initialize undo/redo with initial canvas state
  const undoRedo = useUndoRedo(canvas);
  
  // Update canvas state and push to history
  const updateCanvas = useCallback((newCanvas: CanvasState, options?: { history?: boolean }) => {
    setCanvas(newCanvas);
    if (options?.history !== false) {
      undoRedo.pushState(newCanvas);
    }
  }, [undoRedo]);

  // Update background and push to history
  const updateBackground = useCallback((background: BackgroundConfig | null) => {
    const newCanvas = { ...canvas, background };
    updateCanvas(newCanvas);
  }, [canvas, updateCanvas]);

  // Add element and push to history
  const addElement = useCallback((type: 'text' | 'players' | 'scores' | 'placements', overrides: Partial<any> = {}) => {
    const newElement = type === 'text' 
      ? createTextElement(overrides)
      : createDynamicElement(type, overrides);
    
    const newCanvas = {
      ...canvas,
      elements: [...canvas.elements, newElement]
    };
    updateCanvas(newCanvas);
  }, [canvas, updateCanvas]);

  // Update element and push to history (debounced for position updates)
  const updateElement = useCallback((elementId: string, updates: Partial<CanvasElement>, options?: { debounce?: boolean }) => {
    const newCanvas = {
      ...canvas,
      elements: canvas.elements.map(el => 
        el.id === elementId ? { ...el, ...updates } as CanvasElement : el
      )
    };
    
    // Use debounced history for position updates (dragging)
    const shouldDebounce = options?.debounce && 
      ('x' in updates || 'y' in updates) && 
      Object.keys(updates).length === 1;
    
    updateCanvas(newCanvas, { history: !shouldDebounce });
    if (shouldDebounce) {
      undoRedo.pushState(newCanvas, true);
    }
  }, [canvas, updateCanvas, undoRedo]);

  // Delete element and push to history
  const deleteElement = useCallback((elementId: string) => {
    const newCanvas = {
      ...canvas,
      elements: canvas.elements.filter(el => el.id !== elementId)
    };
    updateCanvas(newCanvas);
  }, [canvas, updateCanvas]);

  // Undo operation
  const undo = useCallback(() => {
    const previousState = undoRedo.undo();
    if (previousState) {
      setCanvas(previousState);
    }
  }, [undoRedo]);

  // Redo operation
  const redo = useCallback(() => {
    const nextState = undoRedo.redo();
    if (nextState) {
      setCanvas(nextState);
    }
  }, [undoRedo]);

  // Clear history (useful after save)
  const clearHistory = useCallback(() => {
    undoRedo.clear();
  }, [undoRedo]);

  // Get serialized data for saving
  const getSerializedData = useCallback(() => {
    return serializeCanvasState(canvas);
  }, [canvas]);

  // Get element by ID
  const getElement = useCallback((elementId: string) => {
    return canvas.elements.find(el => el.id === elementId);
  }, [canvas.elements]);

  // Find element by position (for click detection)
  const getElementAtPosition = useCallback((x: number, y: number): CanvasElement | null => {
    // Check elements in reverse order (top to bottom)
    for (let i = canvas.elements.length - 1; i >= 0; i--) {
      const element = canvas.elements[i];
      const elementWidth = 200; // Approximate width
      const elementHeight = 30; // Approximate height

      if (x >= element.x && x <= element.x + elementWidth &&
          y >= element.y && y <= element.y + elementHeight) {
        return element;
      }
    }
    return null;
  }, [canvas.elements]);

  // Sync undo/redo state when canvas changes from external source
  useEffect(() => {
    const currentState = undoRedo.getCurrentState();
    if (!currentState || JSON.stringify(currentState) !== JSON.stringify(canvas)) {
      // Canvas was updated externally, push to history
      undoRedo.pushState(canvas);
    }
  }, []); // Only run once on mount

  return {
    // State
    canvas,
    elements: canvas.elements,
    background: canvas.background,
    
    // Undo/Redo state
    canUndo: undoRedo.canUndo,
    canRedo: undoRedo.canRedo,
    historyLength: undoRedo.history.length,
    currentIndex: undoRedo.currentIndex,

    // Actions
    updateCanvas,
    updateBackground,
    addElement,
    updateElement,
    deleteElement,
    getElement,
    getElementAtPosition,
    getSerializedData,
    
    // Undo/Redo actions
    undo,
    redo,
    clearHistory,
  };
}
