'use client';

import React from 'react';
import type { DynamicElement, PlayerData } from '@/lib/canvas/types';
import { generateMockData } from '@/lib/canvas/mock-data';
import { cn } from '@/lib/utils';

interface DynamicListProps {
  element: DynamicElement;
  selected?: boolean;
  onSelect?: () => void;
  onDragStart?: (e: React.MouseEvent) => void;
  mode: 'editor' | 'view';
  realData?: PlayerData[];
  readOnly?: boolean;
}

export function DynamicListComponent({ 
  element, 
  selected = false, 
  onSelect, 
  onDragStart,
  mode,
  realData = [],
  readOnly = false 
}: DynamicListProps) {
  // Get display data based on mode
  const displayData = React.useMemo(() => {
    if (mode === 'editor') {
      // Editor mode: show mock data
      return generateMockData(element.type, element.previewCount);
    } else {
      // View mode: show real data
      return getRealData(element, realData);
    }
  }, [element, mode, realData]);

  const handleClick = (e: React.MouseEvent) => {
    if (!readOnly) {
      e.stopPropagation();
      onSelect?.();
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!readOnly) {
      e.stopPropagation();
      onDragStart?.(e);
    }
  };

  return (
    <div
      className={cn(
        'absolute cursor-move select-none',
        // Only apply transition when not dragging
        !selected && 'transition-all duration-75',
        selected && !readOnly && 'ring-2 ring-blue-500 ring-offset-1',
        readOnly && 'pointer-events-none'
      )}
      style={{
        // Use transform for better performance
        transform: `translate(${element.x}px, ${element.y}px)`,
        // Hardware acceleration
        willChange: selected ? 'transform' : 'auto',
        backfaceVisibility: 'hidden',
      }}
      onClick={handleClick}
      onMouseDown={handleMouseDown}
    >
      {displayData.map((text, index) => (
        <div
          key={index}
          style={{
            fontSize: element.fontSize,
            fontFamily: element.fontFamily,
            color: element.color,
            marginBottom: index < displayData.length - 1 ? element.spacing : 0,
            whiteSpace: 'nowrap',
          }}
        >
          {text}
        </div>
      ))}
    </div>
  );
}

// Helper to get real data for view mode
function getRealData(element: DynamicElement, players: PlayerData[]): string[] {
  switch (element.type) {
    case 'players':
      return players.map(p => p.player_name);
    
    case 'scores':
      if (element.roundId && element.roundId !== 'total') {
        return players.map(p => p.round_scores?.[element.roundId]?.toString() || '0');
      }
      return players.map(p => p.total_points.toString());
    
    case 'placements':
      return players.map((_, i) => {
        const num = i + 1;
        const suffix = num === 1 ? 'st' : num === 2 ? 'nd' : num === 3 ? 'rd' : 'th';
        return `${num}${suffix}`;
      });
    
    default:
      return [];
  }
}
