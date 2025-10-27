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
  const [isDragging, setIsDragging] = React.useState(false);

  const handleClick = (e: React.MouseEvent) => {
    if (!readOnly && !isDragging) {
      e.stopPropagation();
      onSelect?.();
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!readOnly) {
      e.stopPropagation();
      setIsDragging(true);
      onDragStart?.(e);
      
      // Reset dragging state on mouse up
      const handleMouseUp = () => {
        setIsDragging(false);
        document.removeEventListener('mouseup', handleMouseUp);
      };
      document.addEventListener('mouseup', handleMouseUp);
    }
  };

  return (
    <div
      className={cn(
        'absolute cursor-move select-none',
        // No transition when dragging or selected
        !selected && !isDragging && 'transition-all duration-75',
        selected && !readOnly && 'ring-2 ring-blue-500 ring-offset-1',
        readOnly && 'pointer-events-none'
      )}
      style={{
        // Use transform for better performance
        transform: `translate(${element.x}px, ${element.y}px)`,
        fontSize: element.fontSize,
        fontFamily: element.fontFamily,
        color: element.color,
        whiteSpace: 'nowrap',
        // Hardware acceleration
        willChange: isDragging ? 'transform' : 'auto',
        backfaceVisibility: 'hidden',
      }}
      onClick={handleClick}
      onMouseDown={handleMouseDown}
    >
      {element.content}
    </div>
  );
}
