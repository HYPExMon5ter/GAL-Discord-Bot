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
        // Removed transition entirely to eliminate jitter
        selected && !readOnly && 'ring-2 ring-blue-500 ring-offset-1',
        readOnly && 'pointer-events-none'
      )}
      style={{
        // Use transform for better performance with integer positions
        transform: `translate(${Math.round(element.x)}px, ${Math.round(element.y)}px)`,
        fontSize: element.fontSize,
        fontFamily: element.fontFamily,
        color: element.color,
        fontWeight: element.bold ? 'bold' : 'normal',
        fontStyle: element.italic ? 'italic' : 'normal',
        textDecoration: element.underline ? 'underline' : 'none',
        whiteSpace: 'nowrap',
        // Hardware acceleration only during drag
        willChange: isDragging ? 'transform' : 'auto',
        backfaceVisibility: 'hidden',
        // Ensure sharp rendering
        WebkitFontSmoothing: 'antialiased',
        MozOsxFontSmoothing: 'grayscale',
      }}
      onClick={handleClick}
      onMouseDown={handleMouseDown}
    >
      {element.content}
    </div>
  );
}
