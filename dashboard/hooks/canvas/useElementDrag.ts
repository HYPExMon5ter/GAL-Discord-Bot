import { useState, useCallback, useRef, useEffect } from 'react';
import type { CanvasElement } from '@/lib/canvas/types';

interface DragState {
  isDragging: boolean;
  draggedElementId: string | null;
  dragStart: { x: number; y: number };
  elementStart: { x: number; y: number };
}

// Throttle function to limit update frequency
function throttle<T extends (...args: any[]) => void>(
  func: T,
  delay: number
): T {
  let timeoutId: NodeJS.Timeout | null = null;
  let lastExecTime = 0;
  
  return ((...args: Parameters<T>) => {
    const currentTime = Date.now();
    
    if (currentTime - lastExecTime > delay) {
      func(...args);
      lastExecTime = currentTime;
    } else {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      timeoutId = setTimeout(() => {
        func(...args);
        lastExecTime = Date.now();
        timeoutId = null;
      }, delay - (currentTime - lastExecTime));
    }
  }) as T;
}

export function useElementDrag() {
  const [dragState, setDragState] = useState<DragState>({
    isDragging: false,
    draggedElementId: null,
    dragStart: { x: 0, y: 0 },
    elementStart: { x: 0, y: 0 },
  });

  // Refs for throttling and performance
  const lastUpdateRef = useRef<{ x: number; y: number } | null>(null);
  const onPositionChangeRef = useRef<(elementId: string, x: number, y: number) => void>(() => {});

  // Start dragging an element
  const startDrag = useCallback((
    elementId: string, 
    element: CanvasElement,
    clientX: number, 
    clientY: number
  ) => {
    setDragState({
      isDragging: true,
      draggedElementId: elementId,
      dragStart: { x: clientX, y: clientY },
      elementStart: { x: element.x, y: element.y },
    });
  }, []);

  // Update drag position with throttling
  const updateDrag = useCallback((clientX: number, clientY: number) => {
    if (!dragState.isDragging || !dragState.draggedElementId) {
      return null;
    }

    const deltaX = clientX - dragState.dragStart.x;
    const deltaY = clientY - dragState.dragStart.y;

    const newPosition = {
      x: dragState.elementStart.x + deltaX,
      y: dragState.elementStart.y + deltaY,
    };

    return {
      elementId: dragState.draggedElementId,
      x: newPosition.x,
      y: newPosition.y,
    };
  }, [dragState]);

  // Throttled version of position update for smoother dragging
  const throttledUpdatePosition = useCallback(
    throttle((elementId: string, x: number, y: number) => {
      // Only update if position changed significantly
      if (!lastUpdateRef.current || 
          Math.abs(x - lastUpdateRef.current.x) > 1 || 
          Math.abs(y - lastUpdateRef.current.y) > 1) {
        onPositionChangeRef.current(elementId, x, y);
        lastUpdateRef.current = { x, y };
      }
    }, 16), // ~60fps
    []
  );

  // End dragging
  const endDrag = useCallback(() => {
    setDragState({
      isDragging: false,
      draggedElementId: null,
      dragStart: { x: 0, y: 0 },
      elementStart: { x: 0, y: 0 },
    });
  }, []);

  // Check if an element is being dragged
  const isDraggingElement = useCallback((elementId: string) => {
    return dragState.draggedElementId === elementId && dragState.isDragging;
  }, [dragState.draggedElementId, dragState.isDragging]);

  // Get drag handlers for an element
  const getElementDragHandlers = useCallback((
    element: CanvasElement,
    onPositionChange: (elementId: string, x: number, y: number) => void
  ) => {
    const handleMouseDown = (e: React.MouseEvent) => {
      e.stopPropagation();
      onPositionChangeRef.current = onPositionChange;
      startDrag(element.id, element, e.clientX, e.clientY);
    };

    const handleMouseMove = (e: MouseEvent) => {
      const dragUpdate = updateDrag(e.clientX, e.clientY);
      if (dragUpdate) {
        throttledUpdatePosition(dragUpdate.elementId, dragUpdate.x, dragUpdate.y);
      }
    };

    const handleMouseUp = () => {
      endDrag();
      lastUpdateRef.current = null;
    };

    return {
      onMouseDown: handleMouseDown,
      onMouseMove: handleMouseMove,
      onMouseUp: handleMouseUp,
    };
  }, [startDrag, updateDrag, endDrag, throttledUpdatePosition]);

  // Global drag state for canvas
  const getGlobalDragHandlers = useCallback((
    onPositionChange: (elementId: string, x: number, y: number) => void
  ) => {
    onPositionChangeRef.current = onPositionChange;
    
    const handleMouseMove = (e: MouseEvent) => {
      const dragUpdate = updateDrag(e.clientX, e.clientY);
      if (dragUpdate) {
        throttledUpdatePosition(dragUpdate.elementId, dragUpdate.x, dragUpdate.y);
      }
    };

    const handleMouseUp = () => {
      endDrag();
      lastUpdateRef.current = null;
    };

    return {
      onMouseMove: handleMouseMove,
      onMouseUp: handleMouseUp,
    };
  }, [updateDrag, endDrag, throttledUpdatePosition]);

  return {
    // State
    isDragging: dragState.isDragging,
    draggedElementId: dragState.draggedElementId,

    // Actions
    startDrag,
    updateDrag,
    endDrag,
    isDraggingElement,

    // Handlers
    getElementDragHandlers,
    getGlobalDragHandlers,
  };
}
