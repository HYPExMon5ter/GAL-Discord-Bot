'use client';

import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { AlertCircle, Clock, RefreshCw } from 'lucide-react';
import type { CanvasLock } from '@/types';

interface LockConflictDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  lock: CanvasLock;
  onCheckStatus: () => void;
  onForceUnlock?: () => void;
}

export function LockConflictDialog({
  isOpen,
  onOpenChange,
  lock,
  onCheckStatus,
  onForceUnlock,
}: LockConflictDialogProps) {
  const formatExpirationTime = (expiresAt: string) => {
    const expireDate = new Date(expiresAt);
    const now = new Date();
    const diffMs = expireDate.getTime() - now.getTime();
    
    if (diffMs <= 0) {
      return 'Expired';
    }
    
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    
    if (diffMinutes < 1) {
      const diffSeconds = Math.floor(diffMs / 1000);
      return `${diffSeconds} second${diffSeconds !== 1 ? 's' : ''}`;
    }
    
    return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''}`;
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-600">
            <AlertCircle className="h-5 w-5" />
            Canvas Locked
          </DialogTitle>
          <DialogDescription>
            This canvas is currently being edited in another browser session.
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="flex items-center gap-3 p-3 rounded-lg bg-yellow-50 border border-yellow-200">
            <Clock className="h-4 w-4 text-yellow-600 flex-shrink-0" />
            <div className="text-sm">
              <p className="font-medium text-yellow-800">
                Lock expires in {formatExpirationTime(lock.expires_at)}
              </p>
              <p className="text-yellow-600">
                You'll be able to edit once the lock expires or is released.
              </p>
            </div>
          </div>

          <div className="text-sm text-muted-foreground">
            <p>
              <strong>Session ID:</strong> {lock.session_id.substring(0, 8)}...
            </p>
            <p>
              <strong>Graphic ID:</strong> {lock.graphic_id}
            </p>
          </div>

          <div className="flex flex-col gap-2">
            <Button 
              onClick={onCheckStatus} 
              variant="outline"
              className="w-full"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Check Status
            </Button>
            
            {onForceUnlock && (
              <Button 
                onClick={onForceUnlock} 
                variant="destructive"
                className="w-full"
              >
                Force Unlock (Admin Only)
              </Button>
            )}
            
            <Button 
              onClick={() => onOpenChange(false)} 
              variant="secondary"
              className="w-full"
            >
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
