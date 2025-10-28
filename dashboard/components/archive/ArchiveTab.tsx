'use client';

import { useState, useCallback, useMemo, useEffect } from 'react';
import { Graphic, ArchivedGraphic } from '@/types';
import { useArchive } from '@/hooks/use-archive';
import { archiveApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { GraphicsTable } from '../graphics/GraphicsTable';
import { CopyGraphicDialog } from '../graphics/CopyGraphicDialog';
import { DeleteConfirmDialog } from '../graphics/DeleteConfirmDialog';
import { Badge } from '@/components/ui/badge';
import { Search, RefreshCw, AlertCircle, Archive, RotateCcw, Trash2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

export function ArchiveTab() {
  const [searchTerm, setSearchTerm] = useState('');
  const [copyDialogOpen, setCopyDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [graphicToCopy, setGraphicToCopy] = useState<Graphic | ArchivedGraphic | null>(null);
  const [graphicToDelete, setGraphicToDelete] = useState<Graphic | ArchivedGraphic | null>(null);
  const [selectedArchivedIds, setSelectedArchivedIds] = useState<number[]>([]);
  const { 
    archivedGraphics, 
    loading, 
    error, 
    refetch, 
    restoreGraphic, 
    permanentDeleteGraphic 
  } = useArchive();
  

  const safeArchivedGraphics = useMemo(
    () => (Array.isArray(archivedGraphics) ? archivedGraphics : []),
    [archivedGraphics],
  );

  const filteredGraphics = useMemo(
    () =>
      safeArchivedGraphics.filter(
        graphic =>
          graphic.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
          (graphic.event_name && graphic.event_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
          graphic.created_by.toLowerCase().includes(searchTerm.toLowerCase()),
      ),
    [safeArchivedGraphics, searchTerm],
  );

  useEffect(() => {
    setSelectedArchivedIds(prev =>
      prev.filter(id => safeArchivedGraphics.some(graphic => graphic.id === id)),
    );
  }, [safeArchivedGraphics]);

  const selectedCount = selectedArchivedIds.length;

  const toggleArchivedSelection = useCallback((id: number) => {
    setSelectedArchivedIds(prev =>
      prev.includes(id) ? prev.filter(existingId => existingId !== id) : [...prev, id],
    );
  }, []);

  const toggleSelectAllVisible = useCallback(
    (selectAll: boolean) => {
      const visibleIds = filteredGraphics.map(graphic => graphic.id);
      setSelectedArchivedIds(prev => {
        if (selectAll) {
          const merged = new Set(prev);
          visibleIds.forEach(id => merged.add(id));
          return Array.from(merged);
        }
        return prev.filter(id => !visibleIds.includes(id));
      });
    },
    [filteredGraphics],
  );

  const handleClearSelection = useCallback(() => {
    setSelectedArchivedIds([]);
  }, []);

  const handleBulkRestore = useCallback(async () => {
    if (selectedArchivedIds.length === 0) {
      return;
    }

    const idsToRestore = selectedArchivedIds.filter(id =>
      safeArchivedGraphics.some(graphic => graphic.id === id),
    );
    if (idsToRestore.length === 0) {
      return;
    }

    const confirmRestore = window.confirm(
      `Restore ${idsToRestore.length} archived graphic${
        idsToRestore.length === 1 ? '' : 's'
      } to Active Graphics?`,
    );
    if (!confirmRestore) {
      return;
    }

    let successCount = 0;
    for (const id of idsToRestore) {
      // eslint-disable-next-line no-await-in-loop
      const success = await restoreGraphic(id);
      if (success) {
        successCount += 1;
      }
    }

    setSelectedArchivedIds(prev => prev.filter(id => !idsToRestore.includes(id)));

    if (successCount > 0) {
      toast.success(successCount === 1 ? 'Graphic restored' : `${successCount} graphics restored`, {
        description:
          successCount === 1
            ? 'Selected graphic moved back to Active Graphics.'
            : 'Selected graphics moved back to Active Graphics.',
      });
    }

    if (successCount !== idsToRestore.length) {
      toast.error('Restore issues', {
        description: `Restored ${successCount} of ${idsToRestore.length} selected graphics.`,
      });
    }
  }, [restoreGraphic, safeArchivedGraphics, selectedArchivedIds]);

  const handleBulkDelete = useCallback(async () => {
    if (selectedArchivedIds.length === 0) {
      return;
    }


    const idsToDelete = selectedArchivedIds.filter(id =>
      safeArchivedGraphics.some(graphic => graphic.id === id),
    );
    if (idsToDelete.length === 0) {
      return;
    }

    const confirmDelete = window.confirm(
      `Permanently delete ${idsToDelete.length} archived graphic${
        idsToDelete.length === 1 ? '' : 's'
      }? This cannot be undone.`,
    );
    if (!confirmDelete) {
      return;
    }

    let successCount = 0;
    for (const id of idsToDelete) {
      // eslint-disable-next-line no-await-in-loop
      const success = await permanentDeleteGraphic(id);
      if (success) {
        successCount += 1;
      }
    }

    setSelectedArchivedIds(prev => prev.filter(id => !idsToDelete.includes(id)));

    if (successCount > 0) {
      toast.success(successCount === 1 ? 'Archived graphic deleted' : `${successCount} graphics deleted`, {
        description:
          successCount === 1
            ? 'Selected archived graphic removed permanently.'
            : 'Selected archived graphics removed permanently.',
      });
    }

    if (successCount !== idsToDelete.length) {
      toast.error('Delete issues', {
        description: `Deleted ${successCount} of ${idsToDelete.length} selected graphics.`,
      });
    }
  }, [permanentDeleteGraphic, safeArchivedGraphics, selectedArchivedIds]);

  const handleRestoreGraphic = useCallback(async (graphic: Graphic | ArchivedGraphic) => {
    try {
      const success = await restoreGraphic(graphic.id);
      if (success) {
        setSelectedArchivedIds(prev => prev.filter(id => id !== graphic.id));
        toast.success('Graphic restored', {
          description: `"${graphic.title}" moved back to Active Graphics.`,
        });
      }
    } catch (error) {
      console.error('Failed to restore graphic:', error);
      toast.error('Restore failed', {
        
        description: `Unable to restore “${graphic.title}”. Please try again.`,
        
      });
    }
  }, [restoreGraphic]);

  const handlePermanentDeleteGraphic = useCallback((graphic: Graphic | ArchivedGraphic) => {
    setGraphicToDelete(graphic);
    setDeleteDialogOpen(true);
  }, []);

  const handleConfirmDelete = useCallback(async (): Promise<boolean> => {
    if (!graphicToDelete) return false;
    const success = await permanentDeleteGraphic(graphicToDelete.id);
    if (success) {
      setSelectedArchivedIds(prev => prev.filter(id => id !== graphicToDelete.id));
      toast.success('Archived graphic deleted', {
        description: `"${graphicToDelete.title}" removed permanently.`,
      });
      setGraphicToDelete(null);
      return true;
    }

    toast.error('Delete failed', {
      description: 'Unable to permanently delete the archived graphic.',
    });
    return false;
  }, [graphicToDelete, permanentDeleteGraphic]);

  const handleDuplicateGraphic = useCallback((graphic: Graphic | ArchivedGraphic) => {
    setGraphicToCopy(graphic);
    setCopyDialogOpen(true);
  }, []);

  const handleCopyGraphic = useCallback(async (title: string, eventName?: string) => {
    if (!graphicToCopy) return false;
    
    try {
      // Convert ArchivedGraphic to Graphic format for copying
      const result = await archiveApi.copyFromArchived(graphicToCopy.id, title, eventName);
      if (result) {
        toast.success('Graphic duplicated', {
          
          description: `Archived graphic “${graphicToCopy.title}” copied into Active Graphics.`,
        });
        return true;
      }
    } catch (error) {
      console.error('Failed to copy archived graphic:', error);
      toast.error('Copy failed', {
        
        description: `Unable to copy “${graphicToCopy.title}”. Please try again.`,
        
      });
    }
    return false;
  }, [graphicToCopy]);

  const handleViewGraphic = useCallback((graphic: Graphic | ArchivedGraphic) => {
    // Open OBS view in new tab
    window.open(`/canvas/view/${graphic.id}`, '_blank');
  }, []);

  if (loading && archivedGraphics.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-6 w-6 animate-spin mr-2" />
        Loading archived graphics...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex-1">
          <h2 className="text-3xl font-bold font-abrau gal-text-gradient-twilight flex items-center justify-center gap-2">
            Archived Graphics
          </h2>
          <p className="text-muted-foreground text-lg text-center">
            View and restore previously archived broadcast graphics
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="flex items-center gap-1 bg-gradient-to-r from-blue-100 to-purple-100 border-purple-200 text-purple-800">
            <Archive className="h-3 w-3 text-purple-600" />
            <span className="flex items-center gap-1">
              {archivedGraphics.length} Archived <span className="text-purple-400">📚</span>
            </span>
          </Badge>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search archived graphics by title or creator..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        
        <Button
          variant="outline"
          size="sm"
          onClick={refetch}
          disabled={loading}
          className="flex items-center gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {safeArchivedGraphics.length > 0 && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearSelection}
              disabled={selectedCount === 0}
            >
              Clear Selection
            </Button>
            <span className="text-sm text-muted-foreground">{selectedCount} selected</span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleBulkRestore}
              disabled={selectedCount === 0}
              className="flex items-center gap-2 text-green-600 hover:text-green-700 hover:bg-green-50"
            >
              <RotateCcw className="h-4 w-4" />
              <span>Restore Selected</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleBulkDelete}
              disabled={selectedCount === 0}
              className="flex items-center gap-2 text-red-600 hover:text-red-700 hover:bg-red-50"
            >
              <Trash2 className="h-4 w-4" />
              <span>Delete Selected</span>
            </Button>
          </div>
        </div>
      )}


      {/* Error State */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-red-800">
              <AlertCircle className="h-5 w-5" />
              <span>{error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Archived Graphics Table */}
      {filteredGraphics.length === 0 ? (
        <Card>
          <CardHeader className="text-center py-12">
            <Archive className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <CardTitle className="text-lg">
              {searchTerm ? 'No archived graphics found' : 'No archived graphics'}
            </CardTitle>
            <CardDescription>
              {searchTerm 
                ? 'Try different search terms or browse all archived graphics'
                : 'Archived graphics will appear here when they are moved from active use'
              }
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <GraphicsTable
              graphics={filteredGraphics}
              loading={loading}
              onEdit={() => {}} // No editing for archived graphics
              onDuplicate={handleDuplicateGraphic}
              onDelete={handlePermanentDeleteGraphic}
              onArchive={handleRestoreGraphic} // Use restore instead of archive
              onView={handleViewGraphic}
              isArchived={true}
              selectable
              selectedIds={selectedArchivedIds}
              onToggleSelect={toggleArchivedSelection}
              onToggleSelectAll={toggleSelectAllVisible}
            />
          </CardContent>
        </Card>
      )}

      {/* Copy Dialog */}
      <CopyGraphicDialog
        open={copyDialogOpen}
        onOpenChange={setCopyDialogOpen}
        onCopy={handleCopyGraphic}
        sourceGraphic={graphicToCopy}
      />

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        graphic={graphicToDelete}
        onConfirm={handleConfirmDelete}
        isArchived={true}
      />
    </div>
  );
}
