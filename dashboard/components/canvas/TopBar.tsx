'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { EventSelector } from '@/components/graphics/EventSelector';
import { ArrowLeft, Save, X, RotateCcw, RotateCw } from 'lucide-react';

interface TopBarProps {
  title: string;
  eventName: string;
  onTitleChange: (title: string) => void;
  onEventNameChange: (eventName: string) => void;
  onSave: () => void;
  onClose: () => void;
  onUndo: () => void;
  onRedo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  saving?: boolean;
  disabled?: boolean;
}

export function TopBar({ 
  title, 
  eventName,
  onTitleChange, 
  onEventNameChange,
  onSave, 
  onClose,
  onUndo,
  onRedo,
  canUndo,
  canRedo,
  saving = false,
  disabled = false 
}: TopBarProps) {
  return (
    <div className="border-b bg-card p-2.5 flex items-end justify-start gap-2">
      {/* Back Button */}
      <Button
        variant="outline"
        size="sm"
        onClick={onClose}
        disabled={saving}
        className="px-3 h-8 shrink-0"
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back
      </Button>

      {/* Divider */}
      <div className="h-8 w-px bg-border mx-1 shrink-0" />

      {/* Title and Event Inputs - FILL AVAILABLE SPACE */}
      <div className="flex-1 flex gap-2 min-w-0">
        <div className="flex-1 min-w-[150px] space-y-1">
          <label className="text-xs text-muted-foreground">Graphic Title</label>
          <Input
            value={title}
            onChange={(e) => onTitleChange(e.target.value)}
            placeholder="Enter graphic title..."
            disabled={saving || disabled}
            className="h-8 text-sm"
          />
        </div>
        <div className="flex-1 min-w-[150px] space-y-1">
          <label className="text-xs text-muted-foreground">Event Name</label>
          <EventSelector
            value={eventName}
            onValueChange={onEventNameChange}
            disabled={saving || disabled}
            className="w-full h-8 text-sm"
          />
        </div>
      </div>

      {/* Divider */}
      <div className="h-8 w-px bg-border mx-1 shrink-0" />

      {/* Undo/Redo Buttons */}
      <div className="flex gap-0.5 shrink-0">
        <Button
          variant="ghost"
          size="sm"
          onClick={onUndo}
          disabled={saving || disabled || !canUndo}
          className="px-2 h-8"
          title="Undo (Ctrl+Z)"
        >
          <RotateCcw className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onRedo}
          disabled={saving || disabled || !canRedo}
          className="px-2 h-8"
          title="Redo (Ctrl+Y)"
        >
          <RotateCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Divider */}
      <div className="h-8 w-px bg-border mx-1 shrink-0" />

      {/* Cancel/Save Buttons */}
      <div className="flex gap-1.5 shrink-0">
        <Button
          variant="outline"
          size="sm"
          onClick={onClose}
          disabled={saving}
          className="px-3 h-8"
        >
          Cancel
        </Button>
        
        <Button
          size="sm"
          onClick={onSave}
          disabled={saving || disabled || !title.trim() || !eventName.trim()}
          className="px-3 h-8"
        >
          <Save className="h-4 w-4 mr-2" />
          {saving ? 'Saving...' : 'Save'}
        </Button>
      </div>
    </div>
  );
}
