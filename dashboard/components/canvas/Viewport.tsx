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
  mode: 'editor' | 'view';
  realData?: any[];
  disabled?: boolean;
}

// Debounce function to limit snap calculations
function debounce<T extends (...args: any[]) => void>(
  func: T,
  delay: number
): T {
  let timeoutId: NodeJS.Timeout | null = null;
  
  return ((...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => {
      func(...args);
    }, delay);
  }) as T;
}

export function Viewport({
  canvas,
  selectedElementId,
  onSelectElement,
  onUpdateElement,
  mode,
  realData = [],
  disabled = false
}: ViewportProps) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);

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

  // Debounced position update for smoother performance
  const debouncedUpdateElement = useCallback(
    debounce((elementId: string, x: number, y: number) => {
      handleElementPositionUpdate(elementId, x, y);
    }, 16), // ~60fps for position updates
    []
  );

  // Handle element position update
  const handleElementPositionUpdate = (elementId: string, x: number, y: number) => {
    if (mode === 'editor' && !disabled) {
      const constrained = constrainToCanvas(
        x, y,
        canvas.background?.width || 1920,
        canvas.background?.height || 1080
      );
      onUpdateElement(elementId, { x: constrained.x, y: constrained.y });
    }
  };

  // Clear dimension cache when elements change
  useEffect(() => {
    clearDimensionCache();
  }, [canvas.elements]);

  // Handle canvas click (deselect element)
  const handleCanvasClick = (e: React.MouseEvent) => {
    if (mode === 'editor' && !disabled) {
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
          onSelectElement(null);
          clearSnapLines();
        }
      }
    }
  };

  // Handle element drag start
  const handleElementDragStart = (element: CanvasElement, e: React.MouseEvent) => {
    if (mode === 'editor' && !disabled) {
      e.stopPropagation();
      onSelectElement(element.id);
      startDrag(element.id, element, e.clientX, e.clientY);
    }
  };

  // Handle element drag (with optimized snapping)
  const handleElementDrag = useCallback(
    debounce((element: CanvasElement, clientX: number, clientY: number) => {
      if (mode === 'editor' && !disabled && isDraggingElement(element.id)) {
        const rect = viewportRef.current?.getBoundingClientRect();
        if (rect) {
          const canvasPos = screenToCanvas(clientX - rect.left, clientY - rect.top);
          
          // Apply snapping with rounding to reduce jitter
          const roundedPos = {
            x: Math.round(canvasPos.x),
            y: Math.round(canvasPos.y)
          };
          const snapped = calculateSnap(element, canvas.elements, roundedPos);
          
          debouncedUpdateElement(element.id, snapped.x, snapped.y);
        }
      }
    }, 8), // Higher frequency debouncing for smooth movement
    [mode, disabled, canvas.elements, calculateSnap, debouncedUpdateElement, isDraggingElement, screenToCanvas]
  );

  // Global mouse event handlers
  useEffect(() => {
    if (mode === 'editor') {
      const { onMouseMove, onMouseUp } = getGlobalDragHandlers(handleElementPositionUpdate);
      
      const handleMouseMove = (e: MouseEvent) => {
        handlePanMove(e);
        onMouseMove(e);
        
        // Handle dragging for current element
        const currentElement = canvas.elements.find(el => el.id === selectedElementId);
        if (currentElement) {
          handleElementDrag(currentElement, e.clientX, e.clientY);
        }
      };

      const handleMouseUp = (e: MouseEvent) => {
        handlePanEnd();
        onMouseUp(e);
        clearSnapLines();
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);

      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [mode, selectedElementId, canvas.elements, handlePanMove, handlePanEnd, getGlobalDragHandlers, handleElementPositionUpdate, clearSnapLines]);

  // Keyboard shortcuts
  useEffect(() => {
    if (mode === 'editor' && !disabled) {
      const handleKeyDown = (e: KeyboardEvent) => {
        // Delete selected element
        if (e.key === 'Delete' && selectedElementId) {
          onUpdateElement(selectedElementId, { /* mark for deletion */ });
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
  }, [mode, disabled, selectedElementId, onSelectElement, onUpdateElement, clearSnapLines]);

  const canvasSize = canvas.background 
    ? { width: canvas.background.width, height: canvas.background.height }
    : { width: 1920, height: 1080 };

  return (
    <div 
      ref={viewportRef}
      className="flex-1 overflow-hidden bg-gray-900 relative"
      onWheel={mode === 'editor' ? handleWheel : undefined}
      onMouseDown={mode === 'editor' ? handlePanStart : undefined}
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
