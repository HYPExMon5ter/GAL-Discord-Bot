'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import type { TextElement } from '@/lib/canvas/types';

interface TextElementProps {
  element: TextElement;
  selected?: boolean;
  onSelect?: () => void;
  onDragStart?: (e: React.MouseEvent) => void;
  readOnly?: boolean;
}

export function TextElementComponent({ 
  element, 
  selected = false, 
  onSelect, 
  onDragStart,
  readOnly = false 
}: TextElementProps) {
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
        'absolute cursor-move select-none transition-all',
        selected && !readOnly && 'ring-2 ring-blue-500 ring-offset-1',
        readOnly && 'pointer-events-none'
      )}
      style={{
        left: element.x,
        top: element.y,
        fontSize: element.fontSize,
        fontFamily: element.fontFamily,
        color: element.color,
        whiteSpace: 'nowrap',
      }}
      onClick={handleClick}
      onMouseDown={handleMouseDown}
    >
      {element.content}
    </div>
  );
}
