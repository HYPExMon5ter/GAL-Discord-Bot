import { useState, useCallback, useRef } from 'react';
import type { CanvasState } from '@/lib/canvas/types';

interface HistoryState {
  canvas: CanvasState;
  timestamp: number;
}

interface UseUndoRedoOptions {
  maxHistorySize?: number;
  debounceMs?: number;
}

export function useUndoRedo(initialState: CanvasState, options: UseUndoRedoOptions = {}) {
  const { maxHistorySize = 50, debounceMs = 100 } = options;
  
  const [history, setHistory] = useState<HistoryState[]>([
    { canvas: initialState, timestamp: Date.now() }
  ]);
  const [currentIndex, setCurrentIndex] = useState(0);
  
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const pendingStateRef = useRef<CanvasState | null>(null);

  // Push new state to history
  const pushState = useCallback((state: CanvasState, debounce = false) => {
    if (debounce) {
      // Debounced push for rapid updates (like dragging)
      pendingStateRef.current = state;
      
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      
      debounceTimerRef.current = setTimeout(() => {
        if (pendingStateRef.current) {
          pushStateImpl(pendingStateRef.current);
          pendingStateRef.current = null;
        }
      }, debounceMs);
      
      return;
    }
    
    // Immediate push
    pushStateImpl(state);
  }, [debounceMs]);

  // Internal implementation of pushing state
  const pushStateImpl = useCallback((state: CanvasState) => {
    setHistory(prev => {
      const newState = { canvas: state, timestamp: Date.now() };
      
      // If we're not at the end of history, truncate future states
      const newHistory = prev.slice(0, currentIndex + 1);
      newHistory.push(newState);
      
      // Limit history size
      if (newHistory.length > maxHistorySize) {
        newHistory.shift();
        setCurrentIndex(newHistory.length - 1);
      } else {
        setCurrentIndex(newHistory.length - 1);
      }
      
      return newHistory;
    });
  }, [currentIndex, maxHistorySize]);

  // Undo operation
  const undo = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex(prev => prev - 1);
      return history[currentIndex - 1].canvas;
    }
    return null;
  }, [currentIndex, history]);

  // Redo operation
  const redo = useCallback(() => {
    if (currentIndex < history.length - 1) {
      setCurrentIndex(prev => prev + 1);
      return history[currentIndex + 1].canvas;
    }
    return null;
  }, [currentIndex, history]);

  // Get current state
  const getCurrentState = useCallback(() => {
    return history[currentIndex]?.canvas;
  }, [history, currentIndex]);

  // Check if can undo
  const canUndo = currentIndex > 0;
  
  // Check if can redo
  const canRedo = currentIndex < history.length - 1;

  // Clear all history (useful for save operations)
  const clear = useCallback(() => {
    const currentState = getCurrentState();
    if (currentState) {
      setHistory([{ canvas: currentState, timestamp: Date.now() }]);
      setCurrentIndex(0);
    }
  }, [getCurrentState]);

  // Cleanup debounce timer on unmount
  useState(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  });

  return {
    // State
    history,
    currentIndex,
    canUndo,
    canRedo,
    
    // Actions
    pushState,
    undo,
    redo,
    getCurrentState,
    clear,
  };
}
