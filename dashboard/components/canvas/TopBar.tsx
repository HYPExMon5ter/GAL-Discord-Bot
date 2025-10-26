'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ArrowLeft, Save, X } from 'lucide-react';

interface TopBarProps {
  title: string;
  onTitleChange: (title: string) => void;
  onSave: () => void;
  onClose: () => void;
  saving?: boolean;
  disabled?: boolean;
}

export function TopBar({ 
  title, 
  onTitleChange, 
  onSave, 
  onClose, 
  saving = false,
  disabled = false 
}: TopBarProps) {
  return (
    <div className="border-b bg-card p-4 flex items-center justify-between">
      <div className="flex items-center gap-4 flex-1">
        <Button
          variant="outline"
          size="sm"
          onClick={onClose}
          disabled={saving}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        
        <div className="flex-1">
          <Input
            value={title}
            onChange={(e) => onTitleChange(e.target.value)}
            placeholder="Enter graphic title..."
            className="text-lg font-semibold"
            disabled={saving || disabled}
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={onClose}
          disabled={saving}
        >
          Cancel
        </Button>
        
        <Button
          size="sm"
          onClick={onSave}
          disabled={saving || disabled || !title.trim()}
        >
          <Save className="h-4 w-4 mr-2" />
          {saving ? 'Saving...' : 'Save'}
        </Button>
      </div>
    </div>
  );
}
