'use client';

import React, { useState, useEffect } from 'react';
import { BackgroundRenderer } from './elements/BackgroundRenderer';
import { TextElementComponent } from './elements/TextElement';
import { DynamicListComponent } from './elements/DynamicList';
import { useTournamentData } from '@/hooks/canvas/useTournamentData';
import { deserializeCanvasState } from '@/lib/canvas/serializer';
import type { CanvasState } from '@/lib/canvas/types';

interface CanvasViewProps {
  graphicId: number;
  onError?: (error: string) => void;
  className?: string;
}

export function CanvasView({ graphicId, onError, className }: CanvasViewProps) {
  const [canvas, setCanvas] = useState<CanvasState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch real tournament data
  const { players, loading: dataLoading, error: dataError } = useTournamentData({
    sortBy: 'total_points',
    sortOrder: 'desc',
  });

  // Load graphic data
  useEffect(() => {
    const loadGraphic = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`/api/graphics/${graphicId}`);
        if (!response.ok) {
          throw new Error(`Failed to load graphic: ${response.statusText}`);
        }

        const data = await response.json();
        const canvasState = deserializeCanvasState(data.data_json);
        setCanvas(canvasState);

      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        setError(errorMessage);
        onError?.(errorMessage);
        console.error('Error loading graphic:', err);
      } finally {
        setLoading(false);
      }
    };

    loadGraphic();
  }, [graphicId, onError]);

  // Handle data errors
  useEffect(() => {
    if (dataError) {
      setError(dataError);
      onError?.(dataError);
    }
  }, [dataError, onError]);

  // Loading state
  if (loading || dataLoading) {
    return (
      <div className={cn("flex items-center justify-center bg-gray-900", className)}>
        <div className="text-center text-white">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-4"></div>
          <p>Loading graphic...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !canvas) {
    return (
      <div className={cn("flex items-center justify-center bg-gray-900", className)}>
        <div className="text-center text-red-400">
          <p className="text-lg font-medium">Error Loading Graphic</p>
          <p className="text-sm">{error || 'Unknown error'}</p>
        </div>
      </div>
    );
  }

  // Get canvas dimensions
  const canvasSize = canvas.background 
    ? { width: canvas.background.width, height: canvas.background.height }
    : { width: 1920, height: 1080 };

  return (
    <div className={cn("bg-gray-900 flex items-center justify-center", className)}>
      <div
        style={{
          width: canvasSize.width,
          height: canvasSize.height,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Background */}
        <BackgroundRenderer 
          background={canvas.background}
          style={{ width: canvasSize.width, height: canvasSize.height }}
        >
          {/* Render Elements with Real Data */}
          {canvas.elements.map((element) => {
            if (element.type === 'text') {
              return (
                <TextElementComponent
                  key={element.id}
                  element={element}
                  readOnly={true}
                />
              );
            } else {
              return (
                <DynamicListComponent
                  key={element.id}
                  element={element}
                  mode="view"
                  realData={players}
                  readOnly={true}
                />
              );
            }
          })}
        </BackgroundRenderer>

        {/* No Data Overlay */}
        {canvas.elements.some(el => el.type !== 'text') && players.length === 0 && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
            <div className="text-center text-white">
              <p className="text-lg font-medium">No Tournament Data</p>
              <p className="text-sm">Dynamic elements will show real data when available</p>
            </div>
          </div>
        )}

        {/* Debug Info (development only) */}
        {process.env.NODE_ENV === 'development' && (
          <div className="absolute top-4 left-4 bg-black/80 text-white text-xs p-2 rounded">
            <div>Graphic ID: {graphicId}</div>
            <div>Elements: {canvas.elements.length}</div>
            <div>Players: {players.length}</div>
            <div>Canvas: {canvasSize.width}x{canvasSize.height}</div>
          </div>
        )}
      </div>
    </div>
  );
}
