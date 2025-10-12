'use client';

import { ArchivedGraphic } from '@/types';
import { useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog';
import { formatDate } from '@/lib/utils';
import { Archive, RotateCcw, Trash2, Calendar, User, AlertTriangle } from 'lucide-react';

interface ArchivedGraphicCardProps {
  graphic: ArchivedGraphic;
  onRestore: (graphic: ArchivedGraphic) => void;
  onPermanentDelete: (graphic: ArchivedGraphic) => void;
  isAdmin?: boolean;
}

export function ArchivedGraphicCard({
  graphic,
  onRestore,
  onPermanentDelete,
  isAdmin = false
}: ArchivedGraphicCardProps) {
  const { username } = useAuth();

  const canRestore = true; // Anyone can restore
  const canDelete = isAdmin; // Only admins can permanently delete

  return (
    <Card className="border-orange-200 bg-orange-50/50 hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg flex items-center gap-2">
              {graphic.title}
              <Badge variant="secondary" className="flex items-center gap-1">
                <Archive className="h-3 w-3" />
                Archived
              </Badge>
            </CardTitle>
            <CardDescription className="mt-1 space-y-1">
              <div className="flex items-center gap-2">
                <User className="h-3 w-3" />
                Created by {graphic.created_by}
              </div>
              <div className="flex items-center gap-2">
                <Calendar className="h-3 w-3" />
                Archived on {formatDate(graphic.archived_at)}
              </div>
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Archive Info */}
        <div className="p-3 rounded-lg bg-orange-100 border border-orange-200 text-orange-800">
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-sm font-medium">Archived Status</span>
          </div>
          <p className="text-xs opacity-75">
            This graphic is currently archived and not available for live use. 
            Restore it to make it active again for editing and broadcasting.
          </p>
          {graphic.restored_from && (
            <p className="text-xs mt-1 opacity-75">
              Restored from version #{graphic.restored_from}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            onClick={() => onRestore(graphic)}
            className="flex items-center gap-1"
          >
            <RotateCcw className="h-3 w-3" />
            Restore to Active
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
                  Delete Forever
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle className="flex items-center gap-2 text-red-600">
                    <AlertTriangle className="h-5 w-5" />
                    Permanent Deletion
                  </AlertDialogTitle>
                  <AlertDialogDescription className="space-y-2">
                    <p>
                      Are you sure you want to permanently delete &quot;{graphic.title}&quot;?
                    </p>
                    <p className="font-medium text-red-600">
                      This will remove all graphic data permanently and cannot be undone.
                    </p>
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => onPermanentDelete(graphic)}
                    className="bg-red-600 hover:bg-red-700"
                  >
                    Delete Permanently
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
