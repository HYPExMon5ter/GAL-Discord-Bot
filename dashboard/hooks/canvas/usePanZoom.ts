import { useState, useCallback, useRef } from 'react';

interface PanZoomState {
  zoom: number;
  pan: { x: number; y: number };
}

const MIN_ZOOM = 0.25;
const MAX_ZOOM = 5.0;
const ZOOM_STEP = 1.2;

export function usePanZoom() {
  const [state, setState] = useState<PanZoomState>({
    zoom: 1,
    pan: { x: 0, y: 0 },
  });

  const isPanningRef = useRef(false);
  const panStartRef = useRef({ x: 0, y: 0 });

  // Set zoom level
  const setZoom = useCallback((zoom: number) => {
    const clampedZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom));
    setState(prev => ({ ...prev, zoom: clampedZoom }));
  }, []);

  // Set pan position
  const setPan = useCallback((x: number, y: number) => {
    setState(prev => ({ ...prev, pan: { x, y } }));
  }, []);

  // Zoom in
  const zoomIn = useCallback(() => {
    setZoom(state.zoom * ZOOM_STEP);
  }, [state.zoom, setZoom]);

  // Zoom out
  const zoomOut = useCallback(() => {
    setZoom(state.zoom / ZOOM_STEP);
  }, [state.zoom, setZoom]);

  // Reset zoom and pan
  const reset = useCallback(() => {
    setState({ zoom: 1, pan: { x: 0, y: 0 } });
  }, []);

  // Fit to screen
  const fitToScreen = useCallback((canvasWidth: number, canvasHeight: number, containerWidth: number, containerHeight: number) => {
    const scaleX = containerWidth / canvasWidth;
    const scaleY = containerHeight / canvasHeight;
    const scale = Math.min(scaleX, scaleY) * 0.9; // 90% of available space

    const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, scale));
    setState({ zoom: newZoom, pan: { x: 0, y: 0 } });
  }, []);

  // Handle wheel zoom
  const handleWheel = useCallback((e: React.WheelEvent) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      setZoom(state.zoom * delta);
    }
  }, [state.zoom, setZoom]);

  // Handle pan start
  const handlePanStart = useCallback((e: React.MouseEvent, isClickOnElement: boolean = false) => {
    // Allow left-click panning only when clicking on empty space (not on elements)
    // Middle mouse or shift+left click always works
    if (e.button === 1 || (e.button === 0 && e.shiftKey) || (e.button === 0 && !isClickOnElement)) {
      e.preventDefault();
      isPanningRef.current = true;
      panStartRef.current = {
        x: e.clientX - state.pan.x,
        y: e.clientY - state.pan.y,
      };
    }
  }, [state.pan]);

  // Handle pan move
  const handlePanMove = useCallback((e: MouseEvent) => {
    if (isPanningRef.current) {
      const newPan = {
        x: e.clientX - panStartRef.current.x,
        y: e.clientY - panStartRef.current.y,
      };
      setPan(newPan.x, newPan.y);
    }
  }, [setPan]);

  // Handle pan end
  const handlePanEnd = useCallback(() => {
    isPanningRef.current = false;
  }, []);

  // Transform coordinates from screen to canvas space
  const screenToCanvas = useCallback((screenX: number, screenY: number) => {
    return {
      x: (screenX - state.pan.x) / state.zoom,
      y: (screenY - state.pan.y) / state.zoom,
    };
  }, [state.zoom, state.pan]);

  // Transform coordinates from canvas to screen space
  const canvasToScreen = useCallback((canvasX: number, canvasY: number) => {
    return {
      x: canvasX * state.zoom + state.pan.x,
      y: canvasY * state.zoom + state.pan.y,
    };
  }, [state.zoom, state.pan]);

  // Get CSS transform string
  const getTransform = useCallback(() => {
    return `scale(${state.zoom}) translate(${state.pan.x / state.zoom}px, ${state.pan.y / state.zoom}px)`;
  }, [state.zoom, state.pan]);

  return {
    // State
    zoom: state.zoom,
    pan: state.pan,

    // Actions
    setZoom,
    setPan,
    zoomIn,
    zoomOut,
    reset,
    fitToScreen,

    // Event handlers
    handleWheel,
    handlePanStart,
    handlePanMove,
    handlePanEnd,

    // Utilities
    screenToCanvas,
    canvasToScreen,
    getTransform,
  };
}
