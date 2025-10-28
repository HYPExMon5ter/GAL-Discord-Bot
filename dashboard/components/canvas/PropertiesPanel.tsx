'use client';

import React from 'react';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Bold, Italic, Underline } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { CanvasElement } from '@/lib/canvas/types';

interface PropertiesPanelProps {
  element: CanvasElement | null;
  onChange: (updates: Partial<CanvasElement>) => void;
  disabled?: boolean;
}

const FONT_OPTIONS = [
  { value: 'Arial', label: 'Arial' },
  { value: 'Helvetica', label: 'Helvetica' },
  { value: 'Georgia', label: 'Georgia' },
  { value: 'Verdana', label: 'Verdana' },
  { value: 'Times New Roman', label: 'Times New Roman' },
  { value: 'Abrau Regular', label: 'Abrau Regular' },
  { value: 'Montserrat', label: 'Montserrat' },
  { value: 'Bebas Neue Regular', label: 'Bebas Neue Regular' },
];

const ROUND_OPTIONS = [
  { value: 'total', label: 'Total Points' },
  { value: 'round_1', label: 'Round 1' },
  { value: 'round_2', label: 'Round 2' },
  { value: 'round_3', label: 'Round 3' },
  { value: 'round_4', label: 'Round 4' },
  { value: 'round_5', label: 'Round 5' },
  { value: 'round_6', label: 'Round 6' },
];

export function PropertiesPanel({ element, onChange, disabled = false }: PropertiesPanelProps) {
  if (!element) {
    return (
      <div className="p-4">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
          Properties
        </h3>
        <div className="text-center py-8 text-muted-foreground">
          <p className="text-sm">No element selected</p>
          <p className="text-xs mt-1">Select an element to edit its properties</p>
        </div>
      </div>
    );
  }

  const handleChange = (field: string, value: any) => {
    onChange({ [field]: value });
  };

  return (
    <div className="p-4 space-y-4">
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        Properties
      </h3>

      {/* Text Content (for text elements only) */}
      {element.type === 'text' && (
        <div>
          <label className="text-xs text-muted-foreground">Content</label>
          <Input
            value={element.content}
            onChange={(e) => handleChange('content', e.target.value)}
            placeholder="Enter text content..."
            disabled={disabled}
          />
        </div>
      )}

      {/* Font Controls (all elements) */}
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-xs text-muted-foreground">Font Family</label>
          <Select
            value={element.fontFamily}
            onValueChange={(value) => handleChange('fontFamily', value)}
            disabled={disabled}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {FONT_OPTIONS.map((font) => (
                <SelectItem key={font.value} value={font.value}>
                  {font.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <label className="text-xs text-muted-foreground">Font Size</label>
          <Input
            type="number"
            min="8"
            max="200"
            value={element.fontSize}
            onChange={(e) => handleChange('fontSize', parseInt(e.target.value) || 16)}
            disabled={disabled}
          />
        </div>
      </div>

      {/* Text Color */}
      <div>
        <label className="text-xs text-muted-foreground">Text Color</label>
        <Input
          type="color"
          value={element.color}
          onChange={(e) => handleChange('color', e.target.value)}
          disabled={disabled}
        />
      </div>

      {/* Text Formatting */}
      <div>
        <label className="text-xs text-muted-foreground">Text Formatting</label>
        <div className="flex gap-1">
          <Button
            type="button"
            variant={element.bold ? "default" : "outline"}
            size="sm"
            onClick={() => handleChange('bold', !element.bold)}
            disabled={disabled}
            className={cn(
              "px-2 h-8",
              element.bold && "bg-primary text-primary-foreground"
            )}
          >
            <Bold className="h-3 w-3" />
          </Button>
          <Button
            type="button"
            variant={element.italic ? "default" : "outline"}
            size="sm"
            onClick={() => handleChange('italic', !element.italic)}
            disabled={disabled}
            className={cn(
              "px-2 h-8",
              element.italic && "bg-primary text-primary-foreground"
            )}
          >
            <Italic className="h-3 w-3" />
          </Button>
          <Button
            type="button"
            variant={element.underline ? "default" : "outline"}
            size="sm"
            onClick={() => handleChange('underline', !element.underline)}
            disabled={disabled}
            className={cn(
              "px-2 h-8",
              element.underline && "bg-primary text-primary-foreground"
            )}
          >
            <Underline className="h-3 w-3" />
          </Button>
        </div>
      </div>

      {/* Dynamic Element Controls */}
      {element.type !== 'text' && (
        <>
          {/* Spacing */}
          <div>
            <label className="text-xs text-muted-foreground">Spacing (px)</label>
            <Input
              type="number"
              min="0"
              max="200"
              value={element.spacing}
              onChange={(e) => handleChange('spacing', parseInt(e.target.value) || 56)}
              disabled={disabled}
            />
          </div>

          {/* Preview Count */}
          <div>
            <label className="text-xs text-muted-foreground">
              Preview Count: {element.previewCount}
            </label>
            <Input
              type="range"
              min="8"
              max="16"
              value={element.previewCount}
              onChange={(e) => handleChange('previewCount', parseInt(e.target.value))}
              disabled={disabled}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Mock items shown in editor. View mode shows all real players.
            </p>
          </div>

          {/* Round Selection (for scores only) */}
          {element.type === 'scores' && (
            <div>
              <label className="text-xs text-muted-foreground">Round</label>
              <Select
                value={element.roundId || 'total'}
                onValueChange={(value) => handleChange('roundId', value)}
                disabled={disabled}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROUND_OPTIONS.map((round) => (
                    <SelectItem key={round.value} value={round.value}>
                      {round.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </>
      )}

      {/* Element Info */}
      <div className="text-xs text-muted-foreground pt-2 border-t space-y-1">
        <p><strong>Type:</strong> {element.type}</p>
        <p><strong>ID:</strong> {element.id.slice(0, 8)}...</p>
        <p><strong>Position:</strong> ({Math.round(element.x)}, {Math.round(element.y)})</p>
      </div>
    </div>
  );
}
