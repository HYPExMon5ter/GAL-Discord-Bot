'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { Trash2, Eye, EyeOff } from 'lucide-react';
import type { CanvasElement } from '@/lib/canvas/types';
import { cn } from '@/lib/utils';

interface LayersTabProps {
  elements: CanvasElement[];
  selectedElementId: string | null;
  onSelectElement: (elementId: string) => void;
  onDeleteElement: (elementId: string) => void;
  disabled?: boolean;
}

export function LayersTab({ 
  elements, 
  selectedElementId, 
  onSelectElement, 
  onDeleteElement,
  disabled = false 
}: LayersTabProps) {
  const getElementLabel = (element: CanvasElement): string => {
    if (element.type === 'text') {
      return `Text: "${element.content}"`;
    } else {
      const typeLabel = element.type.charAt(0).toUpperCase() + element.type.slice(1);
      return `${typeLabel} (${element.previewCount} items)`;
    }
  };

  const getElementIcon = (element: CanvasElement): string => {
    switch (element.type) {
      case 'text': return 'T';
      case 'players': return '👥';
      case 'scores': return '🏆';
      case 'placements': return '🥇';
      default: return '📦';
    }
  };

  return (
    <div className="p-4 space-y-2">
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
        Elements
      </h3>

      {elements.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <p className="text-sm">No elements yet</p>
          <p className="text-xs mt-1">Add elements from the Tools tab</p>
        </div>
      ) : (
        <div className="space-y-1">
          {/* Background */}
          <div className="flex items-center p-2 rounded border bg-muted/50">
            <span className="mr-2">🖼️</span>
            <span className="flex-1 text-sm">Background</span>
            <Eye className="h-4 w-4 text-muted-foreground" />
          </div>

          {/* Elements List */}
          {elements.map((element) => (
            <div
              key={element.id}
              className={cn(
                "flex items-center p-2 rounded border cursor-pointer transition-colors",
                selectedElementId === element.id 
                  ? "bg-primary/20 border-primary/50" 
                  : "hover:bg-muted/50",
                disabled && "opacity-50 cursor-not-allowed"
              )}
              onClick={() => !disabled && onSelectElement(element.id)}
            >
              <span className="mr-2">{getElementIcon(element)}</span>
              <span className="flex-1 text-sm truncate">
                {getElementLabel(element)}
              </span>
              
              <div className="flex items-center gap-1">
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-6 w-6"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (!disabled) onDeleteElement(element.id);
                  }}
                  disabled={disabled}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Element Count */}
      {elements.length > 0 && (
        <div className="text-xs text-muted-foreground pt-2 border-t">
          {elements.length} element{elements.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
}
