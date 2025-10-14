'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Image from 'next/image';
import { graphicsApi } from '@/lib/api';
import { Graphic } from '@/types';

interface CanvasElement {
  id: string;
  type: 'text' | 'player' | 'score' | 'placement' | 'rectangle' | 'circle' | 'image';
  x: number;
  y: number;
  width?: number;
  height?: number;
  content?: string;
  color?: string;
  fontSize?: number;
  fontFamily?: string;
  backgroundColor?: string;
  borderColor?: string;
  borderWidth?: number;
  dataBinding?: string;
}

export default function ObsViewPage() {
  const params = useParams();
  const graphicId = params.id as string;
  const [graphic, setGraphic] = useState<Graphic | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchGraphic = async () => {
      try {
        const data = await graphicsApi.getById(Number(graphicId));
        setGraphic(data);
      } catch (err) {
        console.error('Failed to fetch graphic:', err);
        setError('Failed to load graphic');
      } finally {
        setLoading(false);
      }
    };

    if (graphicId) {
      fetchGraphic();
    }
  }, [graphicId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-black">
        <div className="text-white">Loading graphic...</div>
      </div>
    );
  }

  if (error || !graphic) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-black">
        <div className="text-red-500 text-center">
          <div className="text-xl font-bold mb-2">Error</div>
          <div>{error || 'Graphic not found'}</div>
        </div>
      </div>
    );
  }

  // Note: Archived graphics should still be viewable for reference
  // They just won't auto-update when data binding is implemented

  // Parse canvas data
  let canvasData: { elements?: CanvasElement[], settings?: any, backgroundImage?: string } = {};
  try {
    canvasData = typeof graphic.data_json === 'string' 
      ? JSON.parse(graphic.data_json) 
      : graphic.data_json || {};
  } catch (err) {
    console.error('Failed to parse canvas data:', err);
  }

  const { elements = [], settings = {}, backgroundImage = null } = canvasData;
  
  // Calculate canvas bounds automatically
  const calculateCanvasBounds = () => {
    if (backgroundImage) {
      // If there's a background image, use its dimensions
      return settings;
    }
    
    if (elements.length === 0) {
      // No elements, return default small bounds
      return { width: 500, height: 500, backgroundColor: settings?.backgroundColor || '#000000' };
    }
    
    // Calculate bounds based on element positions
    let minX = Infinity, minY = Infinity;
    let maxX = -Infinity, maxY = -Infinity;
    
    elements.forEach(element => {
      const elementWidth = element.width || (element.type === 'text' ? 100 : 100);
      const elementHeight = element.height || (element.type === 'text' ? 50 : 100);
      
      minX = Math.min(minX, element.x);
      minY = Math.min(minY, element.y);
      maxX = Math.max(maxX, element.x + elementWidth);
      maxY = Math.max(maxY, element.y + elementHeight);
    });
    
    // Add some padding
    const padding = 50;
    const width = Math.max(maxX - minX + padding * 2, 500);
    const height = Math.max(maxY - minY + padding * 2, 500);
    
    return {
      width,
      height,
      backgroundColor: settings?.backgroundColor || '#000000',
      offsetX: -minX + padding,
      offsetY: -minY + padding
    };
  };
  
  const canvasBounds = calculateCanvasBounds();
  const { width = 1920, height = 1080, backgroundColor, offsetX = 0, offsetY = 0 } = canvasBounds;

  return (
    <div 
      className="relative overflow-hidden"
      style={{
        width: '100vw',
        height: '100vh',
        backgroundColor,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}
    >
      <div
        className="relative"
        style={{
          width: `${width}px`,
          height: `${height}px`,
          transform: `scale(min(100vw / ${width}, 100vh / ${height}))`,
          transformOrigin: 'center',
          backgroundImage: backgroundImage ? `url(${backgroundImage})` : 'none',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat'
        }}
      >
        {elements.map((element) => {
          // Calculate dimensions for different element types
          let elementWidth = element.width || 'auto';
          let elementHeight = element.height || 'auto';
          
          if (element.type === 'text' || ['player', 'score', 'placement'].includes(element.type)) {
            // Text elements are auto-sized based on content
            elementWidth = 'auto';
            elementHeight = 'auto';
          } else {
            // Shapes have explicit dimensions
            elementWidth = `${element.width || 100}px`;
            elementHeight = `${element.height || 100}px`;
          }
          
          // Apply offset if we're calculating bounds
          const leftPosition = backgroundImage ? element.x : element.x + offsetX;
          const topPosition = backgroundImage ? element.y : element.y + offsetY;
          
          return (
            <div
              key={element.id}
              className="absolute"
              style={{
                left: `${leftPosition}px`,
                top: `${topPosition}px`,
                width: elementWidth,
                height: elementHeight
              }}
            >
              {(element.type === 'text' || ['player', 'score', 'placement'].includes(element.type)) && (
                <div
                  style={{
                    color: element.color || '#000000',
                    fontSize: `${element.fontSize || 24}px`,
                    fontFamily: element.fontFamily || 'Arial, sans-serif',
                    whiteSpace: 'nowrap',
                    backgroundColor: element.backgroundColor || 'rgba(0, 0, 0, 0)',
                    padding: '4px 8px',
                    borderRadius: '4px'
                  }}
                >
                  {element.content || ''}
                </div>
              )}
              {element.type === 'rectangle' && (
                <div
                  style={{
                    width: '100%',
                    height: '100%',
                    backgroundColor: element.backgroundColor || '#ffffff',
                    border: element.borderColor && element.borderWidth 
                      ? `${element.borderWidth}px solid ${element.borderColor}`
                      : 'none'
                  }}
                />
              )}
              {element.type === 'circle' && (
                <div
                  style={{
                    width: '100%',
                    height: '100%',
                    backgroundColor: element.backgroundColor || '#ffffff',
                    border: element.borderColor && element.borderWidth 
                      ? `${element.borderWidth}px solid ${element.borderColor}`
                      : 'none',
                    borderRadius: '50%'
                  }}
                />
              )}
              {element.type === 'image' && element.content && (
                <div style={{ position: 'relative', width: '100%', height: '100%' }}>
                  <Image
                    src={element.content}
                    alt=""
                    fill
                    style={{
                      objectFit: 'cover'
                    }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
