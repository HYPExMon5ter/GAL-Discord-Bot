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
    <div className="border-b bg-card p-4 flex items-end justify-between gap-4">
      <div className="space-y-1">
        <div className="invisible text-xs text-muted-foreground">Navigation</div>
        <Button
          variant="outline"
          onClick={onClose}
          disabled={saving}
          className="px-3 h-10"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
      </div>

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

      <div className="space-y-1">
        <div className="invisible text-xs text-muted-foreground">Actions</div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={saving}
            className="px-3 h-10"
          >
            Cancel
          </Button>
          
          <Button
            onClick={onSave}
            disabled={saving || disabled || !title.trim() || !eventName.trim()}
            className="px-3 h-10"
          >
            <Save className="h-4 w-4 mr-2" />
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </div>
    </div>
  );
}
