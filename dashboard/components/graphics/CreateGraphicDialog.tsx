'use client';

import { useState } from 'react';
import { CreateGraphicRequest } from '@/types';
import { useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Plus } from 'lucide-react';

interface CreateGraphicDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (data: CreateGraphicRequest) => Promise<boolean>;
}

export function CreateGraphicDialog({ open, onOpenChange, onCreate }: CreateGraphicDialogProps) {
  const [title, setTitle] = useState('');
  const [eventName, setEventName] = useState('');
  const [loading, setLoading] = useState(false);
  

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!title.trim() || !eventName.trim()) return;

    setLoading(true);
    
    try {
      const success = await onCreate({ 
        title: title.trim(),
        event_name: eventName.trim()
      });
      
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

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus className="h-5 w-5" />
            Create New Graphic
          </DialogTitle>
          <DialogDescription>
            Create a new broadcast graphic. You can edit and customize it after creation.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="title" className="text-sm font-medium">Graphic Title</label>
            <Input
              id="title"
              placeholder="Enter a descriptive title for this graphic..."
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              disabled={loading}
              maxLength={100}
            />
            <p className="text-xs text-muted-foreground">
              Choose a clear name that describes the graphic&apos;s purpose or content.
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
              Specify the event this graphic is for (e.g., &quot;Tournament Finals&quot;, &quot;Weekly Show&quot;).
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
              {loading ? 'Creating...' : 'Create & Start Editing'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
