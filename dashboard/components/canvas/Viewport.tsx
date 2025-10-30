'use client';

import React, { useRef, useEffect, useCallback } from 'react';
import { BackgroundRenderer } from './elements/BackgroundRenderer';
import { TextElementComponent } from './elements/TextElement';
import { DynamicListComponent } from './elements/DynamicList';
import type { CanvasState, CanvasElement } from '@/lib/canvas/types';
import { usePanZoom } from '@/hooks/canvas/usePanZoom';
import { useElementDrag } from '@/hooks/canvas/useElementDrag';
import { useSnapping } from '@/hooks/canvas/useSnapping';
import { constrainToCanvas, clearDimensionCache } from '@/lib/canvas/snapping';

interface ViewportProps {
  canvas: CanvasState;
  selectedElementId: string | null;
  onSelectElement: (elementId: string | null) => void;
  onUpdateElement: (elementId: string, updates: Partial<CanvasElement>) => void;
  onDeleteElement: (elementId: string) => void;
  mode: 'editor' | 'view';
  realData?: any[];
  disabled?: boolean;
}

// Removed debounce function - using RAF throttling instead for smoother performance

export function Viewport({
  canvas,
  selectedElementId,
  onSelectElement,
  onUpdateElement,
  onDeleteElement,
  mode,
  realData = [],
  disabled = false
}: ViewportProps) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const isClickOnElementRef = useRef<boolean>(false);

  // Pan/zoom controls
  const {
    zoom,
    pan,
    zoomIn,
    zoomOut,
    handleWheel,
    handlePanStart,
    handlePanMove,
    handlePanEnd,
    screenToCanvas,
    canvasToScreen,
    getTransform,
  } = usePanZoom();

  // Element dragging
  const {
    startDrag,
    isDraggingElement,
    getGlobalDragHandlers,
  } = useElementDrag();

  // Element snapping
  const { snapLines, calculateSnap, clearSnapLines } = useSnapping();

  // Handle element position update
  const handleElementPositionUpdate = useCallback((elementId: string, x: number, y: number) => {
    if (mode === 'editor' && !disabled) {
      const constrained = constrainToCanvas(
        x, y,
        canvas.background?.width || 1920,
        canvas.background?.height || 1080
      );
      onUpdateElement(elementId, { x: constrained.x, y: constrained.y });
    }
  }, [mode, disabled, canvas.background?.width, canvas.background?.height, onUpdateElement]);

  // Clear dimension cache when elements change
  useEffect(() => {
    clearDimensionCache();
  }, [canvas.elements]);

  // Handle canvas mouse down (for panning on empty space)
  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    if (mode === 'editor' && !disabled) {
      // Reset flag
      isClickOnElementRef.current = false;
      
      // Check if clicking on an element
      const rect = viewportRef.current?.getBoundingClientRect();
      if (rect) {
        const canvasPos = screenToCanvas(e.clientX - rect.left, e.clientY - rect.top);
        const clickedElement = canvas.elements.find(element => {
          const elementWidth = 200; // Approximate
          const elementHeight = 30; // Approximate
          return (
            canvasPos.x >= element.x &&
            canvasPos.x <= element.x + elementWidth &&
            canvasPos.y >= element.y &&
            canvasPos.y <= element.y + elementHeight
          );
        });

        if (!clickedElement) {
          // Clicking on empty space
          onSelectElement(null);
          clearSnapLines();
        } else {
          // Clicking on an element
          isClickOnElementRef.current = true;
        }
      }
      
      // Start panning with click context
      handlePanStart(e, isClickOnElementRef.current);
    }
  };

  // Handle canvas click (for deselect)
  const handleCanvasClick = (e: React.MouseEvent) => {
    if (mode === 'editor' && !disabled && !isClickOnElementRef.current) {
      // Only deselect if this wasn't a click on an element
      onSelectElement(null);
      clearSnapLines();
    }
  };

  // Handle element drag start
  const handleElementDragStart = (element: CanvasElement, e: React.MouseEvent) => {
    if (mode === 'editor' && !disabled) {
      e.stopPropagation();
      e.preventDefault(); // Prevent canvas panning when dragging element
      isClickOnElementRef.current = true; // Mark that we're dragging an element
      onSelectElement(element.id);
      startDrag(element.id, element, e.clientX, e.clientY);
    }
  };

  // Handle element drag (receive calculated position, apply constraints and snapping)
  const handleElementDrag = useCallback((element: CanvasElement, x: number, y: number) => {
    if (mode === 'editor' && !disabled && isDraggingElement(element.id)) {
      // Apply snapping with rounding to reduce jitter
      const roundedPos = {
        x: Math.round(x),
        y: Math.round(y)
      };
      const snapped = calculateSnap(element, canvas.elements, roundedPos);
      
      // Direct update - no debouncing
      handleElementPositionUpdate(element.id, snapped.x, snapped.y);
    }
  }, [mode, disabled, canvas.elements, calculateSnap, handleElementPositionUpdate, isDraggingElement]);

  // Global mouse event handlers
  useEffect(() => {
    if (mode === 'editor') {
      // Custom mouse handler that passes calculated position to handleElementDrag
      const handleMouseMove = (e: MouseEvent) => {
        handlePanMove(e);
        
        // Handle dragging for current element (if any)
        if (isClickOnElementRef.current && selectedElementId) {
          const currentElement = canvas.elements.find(el => el.id === selectedElementId);
          if (currentElement) {
            // Calculate canvas position directly
            const rect = viewportRef.current?.getBoundingClientRect();
            if (rect) {
              const canvasPos = screenToCanvas(e.clientX - rect.left, e.clientY - rect.top);
              // Pass calculated position to handler
              handleElementDrag(currentElement, canvasPos.x, canvasPos.y);
            }
          }
        }
      };

      const handleMouseUp = (e: MouseEvent) => {
        isClickOnElementRef.current = false; // Reset flag
        handlePanEnd();
        clearSnapLines();
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);

      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [mode, selectedElementId, canvas.elements, handlePanMove, handlePanEnd, screenToCanvas, handleElementDrag, clearSnapLines]);

  // Keyboard shortcuts
  useEffect(() => {
    if (mode === 'editor' && !disabled) {
      const handleKeyDown = (e: KeyboardEvent) => {
        // Delete selected element
        if (e.key === 'Delete' && selectedElementId) {
          onDeleteElement(selectedElementId);
          onSelectElement(null);
        }
        // Escape to deselect
        if (e.key === 'Escape') {
          onSelectElement(null);
          clearSnapLines();
        }
      };

      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [mode, disabled, selectedElementId, onSelectElement, onDeleteElement, clearSnapLines]);

  const canvasSize = canvas.background 
    ? { width: canvas.background.width, height: canvas.background.height }
    : { width: 1920, height: 1080 };

  return (
    <div 
      ref={viewportRef}
      className="flex-1 overflow-hidden bg-gray-900 relative"
      onWheel={mode === 'editor' ? handleWheel : undefined}
      onMouseDown={mode === 'editor' ? handleCanvasMouseDown : undefined}
      onClick={handleCanvasClick}
    >
      {/* Canvas Container */}
      <div 
        ref={canvasRef}
        className="absolute"
        style={{
          width: canvasSize.width,
          height: canvasSize.height,
          transform: getTransform(),
          transformOrigin: 'top left',
        }}
      >
        {/* Background */}
        <BackgroundRenderer background={canvas.background}>
          {/* Render Elements */}
          {canvas.elements.map((element) => {
            if (element.type === 'text') {
              return (
                <TextElementComponent
                  key={element.id}
                  element={element}
                  selected={selectedElementId === element.id}
                  onSelect={() => mode === 'editor' && onSelectElement(element.id)}
                  onDragStart={(e) => handleElementDragStart(element, e)}
                  readOnly={mode === 'view' || disabled}
                />
              );
            } else {
              return (
                <DynamicListComponent
                  key={element.id}
                  element={element}
                  selected={selectedElementId === element.id}
                  onSelect={() => mode === 'editor' && onSelectElement(element.id)}
                  onDragStart={(e) => handleElementDragStart(element, e)}
                  mode={mode}
                  realData={realData}
                  readOnly={mode === 'view' || disabled}
                />
              );
            }
          })}
        </BackgroundRenderer>
      </div>

      {/* Snap Lines */}
      {mode === 'editor' && snapLines.map((line, index) => (
        <div
          key={index}
          className="absolute bg-blue-500 pointer-events-none"
          style={{
            ...(line.x && {
              left: line.x,
              top: 0,
              width: 1,
              height: '100%',
            }),
            ...(line.y && {
              left: 0,
              top: line.y,
              width: '100%',
              height: 1,
            }),
          }}
        />
      ))}

      {/* Zoom Controls */}
      {mode === 'editor' && (
        <div className="absolute bottom-4 right-4 bg-background/80 backdrop-blur-sm rounded-lg border p-2 flex items-center gap-2">
          <button
            className="w-8 h-8 rounded hover:bg-muted flex items-center justify-center text-sm"
            onClick={zoomOut}
            disabled={disabled}
          >
            -
          </button>
          <span className="text-xs px-2 min-w-[60px] text-center">
            {Math.round(zoom * 100)}%
          </span>
          <button
            className="w-8 h-8 rounded hover:bg-muted flex items-center justify-center text-sm"
            onClick={zoomIn}
            disabled={disabled}
          >
            +
          </button>
        </div>
      )}

      {/* Canvas Info */}
      <div className="absolute top-4 right-4 bg-background/80 backdrop-blur-sm rounded-lg border px-3 py-2">
        <div className="text-xs text-muted-foreground">
          {canvasSize.width} × {canvasSize.height}px
        </div>
        {mode === 'editor' && (
          <div className="text-xs text-muted-foreground">
            {canvas.elements.length} element{canvas.elements.length !== 1 ? 's' : ''}
          </div>
        )}
      </div>
    </div>
  );
}
