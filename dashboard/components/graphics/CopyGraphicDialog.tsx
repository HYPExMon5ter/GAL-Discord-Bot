'use client';

import React, { useState } from 'react';
import { Graphic, ArchivedGraphic } from '@/types';
import { useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Copy } from 'lucide-react';

interface CopyGraphicDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCopy: (title: string, eventName?: string) => Promise<boolean>;
  sourceGraphic: Graphic | ArchivedGraphic | null;
}

export function CopyGraphicDialog({ open, onOpenChange, onCopy, sourceGraphic }: CopyGraphicDialogProps) {
  const [title, setTitle] = useState('');
  const [eventName, setEventName] = useState('');
  const [loading, setLoading] = useState(false);
  const { username } = useAuth();

  // Reset form when dialog opens or source graphic changes
  React.useEffect(() => {
    if (open && sourceGraphic) {
      setTitle(`${sourceGraphic.title} (Copy)`);
      setEventName(sourceGraphic.event_name || '');
    } else if (!open) {
      setTitle('');
      setEventName('');
    }
  }, [open, sourceGraphic]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!title.trim() || !eventName.trim() || !sourceGraphic) return;

    setLoading(true);
    
    try {
      const success = await onCopy(
        title.trim(),
        eventName.trim()
      );
      
      if (success) {
        setTitle('');
        setEventName('');
        onOpenChange(false);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      setTitle('');
      setEventName('');
      onOpenChange(false);
    }
  };

  if (!sourceGraphic) return null;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Copy className="h-5 w-5" />
            Copy Graphic
          </DialogTitle>
          <DialogDescription>
            Create a copy of &quot;{sourceGraphic.title}&quot;. You can customize the title and event name for the new graphic.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="title" className="text-sm font-medium">Graphic Title</label>
            <Input
              id="title"
              placeholder="Enter a title for the copied graphic..."
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              disabled={loading}
              maxLength={100}
            />
            <p className="text-xs text-muted-foreground">
              Choose a unique name for this copy of the graphic.
            </p>
          </div>

          <div className="space-y-2">
            <label htmlFor="eventName" className="text-sm font-medium">Event Name *</label>
            <Input
              id="eventName"
              placeholder="Enter the event name..."
              value={eventName}
              onChange={(e) => setEventName(e.target.value)}
              required
              disabled={loading}
              maxLength={100}
            />
            <p className="text-xs text-muted-foreground">
              Specify the event this copied graphic is for.
            </p>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!title.trim() || !eventName.trim() || loading}
            >
              {loading ? 'Copying...' : 'Copy Graphic'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
