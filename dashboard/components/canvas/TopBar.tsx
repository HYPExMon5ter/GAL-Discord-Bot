'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { EventSelector } from '@/components/graphics/EventSelector';
import { ArrowLeft, Save, X } from 'lucide-react';

interface TopBarProps {
  title: string;
  eventName: string;
  onTitleChange: (title: string) => void;
  onEventNameChange: (eventName: string) => void;
  onSave: () => void;
  onClose: () => void;
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
  saving = false,
  disabled = false 
}: TopBarProps) {
  return (
    <div className="border-b bg-card p-4 flex items-center justify-between gap-4">
      <Button
        variant="outline"
        onClick={onClose}
        disabled={saving}
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back
      </Button>

      <div className="flex-1 flex gap-3">
        <div className="flex-1 space-y-1">
          <label className="text-xs text-muted-foreground">Graphic Title</label>
          <Input
            value={title}
            onChange={(e) => onTitleChange(e.target.value)}
            placeholder="Enter graphic title..."
            disabled={saving || disabled}
          />
        </div>
        <div className="flex-1 space-y-1">
          <label className="text-xs text-muted-foreground">Event Name</label>
          <EventSelector
            value={eventName}
            onValueChange={onEventNameChange}
            disabled={saving || disabled}
            className="w-full"
          />
        </div>
      </div>

      <div className="flex items-end gap-2 pb-[1px]">
        <Button
          variant="outline"
          onClick={onClose}
          disabled={saving}
        >
          Cancel
        </Button>
        
        <Button
          onClick={onSave}
          disabled={saving || disabled || !title.trim() || !eventName.trim()}
        >
          <Save className="h-4 w-4 mr-2" />
          {saving ? 'Saving...' : 'Save'}
        </Button>
      </div>
    </div>
  );
}
