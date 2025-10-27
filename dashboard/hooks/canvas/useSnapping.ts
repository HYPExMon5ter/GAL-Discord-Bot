import { useState, useCallback, useRef } from 'react';
import type { CanvasElement } from '@/lib/canvas/types';
import { calculateElementSnapping } from '@/lib/canvas/snapping';

interface SnapLine {
  x?: number;
  y?: number;
  type: 'horizontal' | 'vertical';
}

export function useSnapping() {
  const [snapLines, setSnapLines] = useState<SnapLine[]>([]);

  // Calculate snap position for an element
  const calculateSnap = useCallback((
    element: CanvasElement,
    elements: CanvasElement[],
    currentPosition: { x: number; y: number },
    threshold?: { horizontal: number; vertical: number }
  ) => {
    const result = calculateElementSnapping(element, elements, currentPosition, threshold);
    
    // Update snap lines for visual feedback
    setSnapLines(result.snapLines);
    
    return {
      x: result.x,
      y: result.y,
      hasSnapX: result.snapLines.some(line => line.type === 'vertical'),
      hasSnapY: result.snapLines.some(line => line.type === 'horizontal'),
    };
  }, []);

  // Clear snap lines
  const clearSnapLines = useCallback(() => {
    setSnapLines([]);
  }, []);

  // Check if position should snap (for preview)
  const shouldSnap = useCallback((
    element: CanvasElement,
    elements: CanvasElement[],
    currentPosition: { x: number; y: number },
    threshold = { horizontal: 8, vertical: 8 }
  ) => {
    const result = calculateElementSnapping(element, elements, currentPosition, threshold);
    return {
      snapped: result.x !== currentPosition.x || result.y !== currentPosition.y,
      snapX: result.x,
      snapY: result.y,
    };
  }, []);

  return {
    // State
    snapLines,

    // Actions
    calculateSnap,
    clearSnapLines,
    shouldSnap,
  };
}
