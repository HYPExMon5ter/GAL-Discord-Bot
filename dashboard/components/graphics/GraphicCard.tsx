'use client';

import { useState, useEffect } from 'react';
import { Graphic, CanvasLock } from '@/types';
import { useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog';

import { Edit, Copy, Trash2, Archive } from 'lucide-react';

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
  
  

  const formatDate = (value: string | undefined) => {
    if (!value) return '—';
    const date = new Date(value);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const canEdit = true;
  const canDelete = true;

  return (
    <Card className="transition-all duration-300">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              {graphic.title}
            </CardTitle>
            <CardDescription className="mt-1 text-muted-foreground">
              Created by <span className="text-primary font-medium">{graphic.created_by}</span> • Updated {formatDate(graphic.updated_at)}
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">

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
            Edit Graphic
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={() => onDuplicate(graphic)}
            className="flex items-center gap-1 hover:border-primary/50 hover:bg-primary/5"
          >
            <Copy className="h-3 w-3" />
            Duplicate
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={() => onArchive(graphic)}
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
