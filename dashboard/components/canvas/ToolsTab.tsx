'use client';

import React, { useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Upload, Type, Users, Trophy, Medal } from 'lucide-react';

interface ToolsTabProps {
  onAddElement: (type: 'text' | 'players' | 'scores' | 'placements') => void;
  onBackgroundUpload: (file: File) => void;
  disabled?: boolean;
}

export function ToolsTab({ onAddElement, onBackgroundUpload, disabled = false }: ToolsTabProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleBackgroundUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      onBackgroundUpload(file);
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="p-4 space-y-4">
      <div>
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
          Canvas Tools
        </h3>
        
        <div className="space-y-2">
          {/* Background Upload */}
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
          >
            <Upload className="h-4 w-4 mr-2" />
            Upload Background
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleBackgroundUpload}
            className="hidden"
          />

          {/* Text Element */}
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start"
            onClick={() => onAddElement('text')}
            disabled={disabled}
          >
            <Type className="h-4 w-4 mr-2" />
            Add Text
          </Button>

          {/* Dynamic Elements */}
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start"
            onClick={() => onAddElement('players')}
            disabled={disabled}
          >
            <Users className="h-4 w-4 mr-2" />
            Add Players
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start"
            onClick={() => onAddElement('scores')}
            disabled={disabled}
          >
            <Trophy className="h-4 w-4 mr-2" />
            Add Scores
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start"
            onClick={() => onAddElement('placements')}
            disabled={disabled}
          >
            <Medal className="h-4 w-4 mr-2" />
            Add Placements
          </Button>
        </div>
      </div>

    </div>
  );
}
