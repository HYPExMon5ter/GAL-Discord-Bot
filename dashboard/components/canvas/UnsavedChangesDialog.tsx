'use client';

import { useState } from 'react';
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { AlertTriangle, Save, X } from 'lucide-react';

interface UnsavedChangesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: () => Promise<void>;
  onDiscard: () => void;
  saving?: boolean;
}

export function UnsavedChangesDialog({ 
  open, 
  onOpenChange, 
  onSave,
  onDiscard,
  saving = false 
}: UnsavedChangesDialogProps) {
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSave();
      onOpenChange(false);
    } catch (error) {
      console.error('Failed to save before closing:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDiscard = () => {
    if (!isSaving) {
      onDiscard();
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="sm:max-w-[425px]">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2 text-orange-600">
            <AlertTriangle className="h-5 w-5" />
            Unsaved Changes
          </AlertDialogTitle>
          <AlertDialogDescription>
            You have unsaved changes to your graphic. What would you like to do?
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="space-y-4">
          <div className="flex items-start gap-3 p-3 bg-orange-50 border border-orange-200 rounded-lg">
            <AlertTriangle className="h-5 w-5 text-orange-600 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-orange-800">
              If you don&apos;t save your changes, all modifications will be lost.
            </div>
          </div>

          <div className="grid gap-2 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <Save className="h-4 w-4" />
              <span>Save your changes before leaving</span>
            </div>
            <div className="flex items-center gap-2">
              <X className="h-4 w-4" />
              <span>Discard all changes and close</span>
            </div>
          </div>
        </div>

        <AlertDialogFooter>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDiscard}
            disabled={isSaving || saving}
          >
            Discard Changes
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={isSaving || saving}
          >
            {isSaving || saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
