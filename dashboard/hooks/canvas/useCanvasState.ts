import { useState, useCallback } from 'react';
import type { CanvasState, CanvasElement, BackgroundConfig } from '@/lib/canvas/types';
import { serializeCanvasState, deserializeCanvasState } from '@/lib/canvas/serializer';
import { createTextElement, createDynamicElement } from '@/lib/canvas/element-factory';

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

  // Update entire canvas state
  const updateCanvas = useCallback((newCanvas: CanvasState) => {
    setCanvas(newCanvas);
  }, []);

  // Update background
  const updateBackground = useCallback((background: BackgroundConfig | null) => {
    setCanvas(prev => ({ ...prev, background }));
  }, []);

  // Add element
  const addElement = useCallback((type: 'text' | 'players' | 'scores' | 'placements', overrides: Partial<any> = {}) => {
    const newElement = type === 'text' 
      ? createTextElement(overrides)
      : createDynamicElement(type, overrides);
    
    setCanvas(prev => ({
      ...prev,
      elements: [...prev.elements, newElement]
    }));
  }, []);

  // Update element
  const updateElement = useCallback((elementId: string, updates: Partial<CanvasElement>) => {
    setCanvas(prev => ({
      ...prev,
      elements: prev.elements.map(el => 
        el.id === elementId ? { ...el, ...updates } : el
      )
    }));
  }, []);

  // Delete element
  const deleteElement = useCallback((elementId: string) => {
    setCanvas(prev => ({
      ...prev,
      elements: prev.elements.filter(el => el.id !== elementId)
    }));
  }, []);

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

  return {
    // State
    canvas,
    elements: canvas.elements,
    background: canvas.background,

    // Actions
    updateCanvas,
    updateBackground,
    addElement,
    updateElement,
    deleteElement,
    getElement,
    getElementAtPosition,
    getSerializedData,
  };
}
