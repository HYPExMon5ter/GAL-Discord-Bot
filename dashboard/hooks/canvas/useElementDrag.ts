import { useState, useCallback, useRef } from 'react';
import type { CanvasElement } from '@/lib/canvas/types';

interface DragState {
  isDragging: boolean;
  draggedElementId: string | null;
  dragStart: { x: number; y: number };
  elementStart: { x: number; y: number };
}

export function useElementDrag() {
  const [dragState, setDragState] = useState<DragState>({
    isDragging: false,
    draggedElementId: null,
    dragStart: { x: 0, y: 0 },
    elementStart: { x: 0, y: 0 },
  });

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

  // Update drag position
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
      startDrag(element.id, element, e.clientX, e.clientY);
    };

    const handleMouseMove = (e: MouseEvent) => {
      const dragUpdate = updateDrag(e.clientX, e.clientY);
      if (dragUpdate) {
        onPositionChange(dragUpdate.elementId, dragUpdate.x, dragUpdate.y);
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
  }, [startDrag, updateDrag, endDrag]);

  // Global drag state for canvas
  const getGlobalDragHandlers = useCallback((
    onPositionChange: (elementId: string, x: number, y: number) => void
  ) => {
    const handleMouseMove = (e: MouseEvent) => {
      const dragUpdate = updateDrag(e.clientX, e.clientY);
      if (dragUpdate) {
        onPositionChange(dragUpdate.elementId, dragUpdate.x, dragUpdate.y);
      }
    };

    const handleMouseUp = () => {
      endDrag();
    };

    return {
      onMouseMove: handleMouseMove,
      onMouseUp: handleMouseUp,
    };
  }, [updateDrag, endDrag]);

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
