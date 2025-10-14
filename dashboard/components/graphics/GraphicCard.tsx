'use client';

import { useState, useEffect } from 'react';
import { Graphic, CanvasLock } from '@/types';
import { useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog';
import { formatTimeRemaining, formatDate } from '@/lib/utils';
import { Edit, Copy, Trash2, Archive, Lock, Clock, User } from 'lucide-react';

interface GraphicCardProps {
  graphic: Graphic;
  lock?: CanvasLock;
  onEdit: (graphic: Graphic) => void;
  onDuplicate: (graphic: Graphic) => void;
  onDelete: (graphic: Graphic) => void;
  onArchive: (graphic: Graphic) => void;
}

export function GraphicCard({
  graphic,
  lock,
  onEdit,
  onDuplicate,
  onDelete,
  onArchive
}: GraphicCardProps) {
  const { username } = useAuth();
  const [timeRemaining, setTimeRemaining] = useState('');

  const isLocked = lock?.locked && lock.user_name !== username;
  const isLockedByMe = lock?.locked && lock.user_name === username;
  const canEdit = !isLocked;
  const canDelete = !isLocked && graphic.created_by === username;

  useEffect(() => {
    if (lock?.expires_at) {
      const updateTime = () => {
        setTimeRemaining(formatTimeRemaining(new Date(lock.expires_at)));
      };

      updateTime();
      const interval = setInterval(updateTime, 1000);

      return () => clearInterval(interval);
    }
  }, [lock]);

  return (
    <Card className={`${isLocked ? 'opacity-75 border-primary/50' : ''} transition-all duration-300 hover:shadow-lg hover:shadow-primary/10`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              {graphic.title}
              {isLocked && (
                <Badge variant="secondary" className="flex items-center gap-1 bg-gradient-to-r from-orange-500 to-orange-600 text-white border-0">
                  <Lock className="h-3 w-3" />
                  In Use
                </Badge>
              )}
            </CardTitle>
            <CardDescription className="mt-1 text-muted-foreground">
              Created by <span className="text-primary font-medium">{graphic.created_by}</span> • Updated {formatDate(graphic.updated_at)}
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Lock Status */}
        {lock?.locked && (
          <div className={`p-3 rounded-xl border transition-all duration-200 ${
            isLockedByMe 
              ? 'bg-gradient-to-r from-green-500/10 to-emerald-600/10 border-green-500/30 text-green-300' 
              : 'bg-gradient-to-r from-orange-500/10 to-red-500/10 border-orange-500/30 text-orange-300'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Lock className="h-4 w-4" />
                <span className="text-sm font-medium">
                  {isLockedByMe 
                    ? 'You are editing this graphic' 
                    : `Editing by ${lock.user_name}`
                  }
                </span>
              </div>
              {timeRemaining && (
                <div className="flex items-center gap-1 text-xs opacity-80">
                  <Clock className="h-3 w-3" />
                  {timeRemaining}
                </div>
              )}
            </div>
            <div className="text-xs mt-1 opacity-70">
              Session started at {formatDate(lock.locked_at)}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="galOutline"
            onClick={() => onEdit(graphic)}
            disabled={!canEdit}
            className="flex items-center gap-1"
          >
            <Edit className="h-3 w-3" />
            {isLockedByMe ? 'Continue Editing' : 'Edit Graphic'}
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={() => onDuplicate(graphic)}
            disabled={isLocked}
            className="flex items-center gap-1 hover:border-primary/50 hover:bg-primary/5"
          >
            <Copy className="h-3 w-3" />
            Duplicate
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={() => onArchive(graphic)}
            disabled={!canEdit}
            className="flex items-center gap-1 hover:border-primary/50 hover:bg-primary/5"
          >
            <Archive className="h-3 w-3" />
            Archive
          </Button>

          {canDelete && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  size="sm"
                  variant="destructive"
                  className="flex items-center gap-1"
                >
                  <Trash2 className="h-3 w-3" />
                  Delete
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent className="gal-card">
                <AlertDialogHeader>
                  <AlertDialogTitle className="text-foreground">Delete Graphic</AlertDialogTitle>
                  <AlertDialogDescription className="text-muted-foreground">
                    Are you sure you want to delete &quot;{graphic.title}&quot;? This action cannot be undone and will remove the graphic permanently.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel className="hover:bg-muted">Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={() => onDelete(graphic)} className="gal-button-primary">
                    Delete Forever
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
