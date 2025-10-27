import { useState, useCallback, useRef, useEffect } from 'react';
import type { CanvasElement } from '@/lib/canvas/types';

interface DragState {
  isDragging: boolean;
  draggedElementId: string | null;
}

// RAF throttling removed - direct updates provide better responsiveness

export function useElementDrag() {
  const [dragState, setDragState] = useState<DragState>({
    isDragging: false,
    draggedElementId: null,
  });

  // Refs for drag state (avoid stale closures)
  const dragStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const elementStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const elementIdRef = useRef<string | null>(null);
  const onPositionChangeRef = useRef<(elementId: string, x: number, y: number) => void>(() => {});

  // Start dragging an element
  const startDrag = useCallback((
    elementId: string, 
    element: CanvasElement,
    clientX: number, 
    clientY: number
  ) => {
    // Store drag state in refs to avoid stale closures
    dragStartRef.current = { x: clientX, y: clientY };
    elementStartRef.current = { x: element.x, y: element.y };
    elementIdRef.current = elementId;
    
    setDragState({
      isDragging: true,
      draggedElementId: elementId,
    });
  }, []);

  // Update drag position (direct, no throttling)
  const updateDrag = useCallback((clientX: number, clientY: number) => {
    // Check refs instead of state to avoid stale closures
    if (!dragState.isDragging || !elementIdRef.current) {
      return null;
    }

    const deltaX = clientX - dragStartRef.current.x;
    const deltaY = clientY - dragStartRef.current.y;

    const newPosition = {
      x: elementStartRef.current.x + deltaX,
      y: elementStartRef.current.y + deltaY,
    };

    return {
      elementId: elementIdRef.current,
      x: newPosition.x,
      y: newPosition.y,
    };
  }, [dragState.isDragging]);

  // Direct position update (no RAF throttling)
  const updatePosition = useCallback((elementId: string, x: number, y: number) => {
    // Only update if we're still dragging this element
    if (dragState.isDragging && elementIdRef.current === elementId) {
      onPositionChangeRef.current(elementId, x, y);
    }
  }, [dragState.isDragging]);

  // End dragging
  const endDrag = useCallback(() => {
    // Clear refs immediately
    elementIdRef.current = null;
    
    setDragState({
      isDragging: false,
      draggedElementId: null,
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
        updatePosition(dragUpdate.elementId, dragUpdate.x, dragUpdate.y);
      }
    };

    const handleMouseUp = () => {
      endDrag();
    };

    return {
      onMouseDown: handleMouseDown,
      onMouseMove: handleMouseMove,
      onMouseUp: handleMouseUp,
    };
  }, [startDrag, updateDrag, endDrag, updatePosition]);

  // Global drag state for canvas
  const getGlobalDragHandlers = useCallback((
    onPositionChange: (elementId: string, x: number, y: number) => void
  ) => {
    onPositionChangeRef.current = onPositionChange;
    
    const handleMouseMove = (e: MouseEvent) => {
      const dragUpdate = updateDrag(e.clientX, e.clientY);
      if (dragUpdate) {
        updatePosition(dragUpdate.elementId, dragUpdate.x, dragUpdate.y);
      }
    };

    const handleMouseUp = () => {
      endDrag();
    };

    return {
      onMouseMove: handleMouseMove,
      onMouseUp: handleMouseUp,
    };
  }, [updateDrag, endDrag, updatePosition]);

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
