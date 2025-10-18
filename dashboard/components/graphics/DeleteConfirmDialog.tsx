'use client';

import { useState } from 'react';
import { Graphic, ArchivedGraphic } from '@/types';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { AlertTriangle, Trash2 } from 'lucide-react';

interface DeleteConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  graphic: Graphic | ArchivedGraphic | null;
  onConfirm: () => Promise<boolean>;
  isArchived?: boolean;
}

export function DeleteConfirmDialog({ 
  open, 
  onOpenChange, 
  graphic, 
  onConfirm,
  isArchived = false 
}: DeleteConfirmDialogProps) {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleConfirm = async () => {
    if (!graphic) return;
    
    setIsDeleting(true);
    try {
      const success = await onConfirm();
      if (success) {
        onOpenChange(false);
      }
    } catch (error) {
      console.error('Failed to delete graphic:', error);
    } finally {
      setIsDeleting(false);
    }
  };

  if (!graphic) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-600">
            <Trash2 className="h-5 w-5" />
            Delete Graphic
          </DialogTitle>
          <DialogDescription>
            Are you sure you want to delete this graphic? This action cannot be undone.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex items-start gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
            <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-red-800">
              {isArchived 
                ? "This will permanently delete the archived graphic and all its data. This action cannot be undone."
                : "This will permanently delete the active graphic and all its data. This action cannot be undone."
              }
            </div>
          </div>

          <div className="p-3 bg-gray-50 rounded border">
            <div className="text-sm font-medium text-gray-900">{graphic.title}</div>
            {graphic.event_name && (
              <div className="text-sm text-gray-600">Event: {graphic.event_name}</div>
            )}
            <div className="text-xs text-gray-500 mt-1">
              {isArchived ? 'Archived' : 'Active'} Graphic - ID: {graphic.id}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={isDeleting}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={handleConfirm}
            disabled={isDeleting}
          >
            {isDeleting ? 'Deleting...' : 'Delete Graphic'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
