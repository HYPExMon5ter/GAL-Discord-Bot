'use client';

import { useState, useCallback, useMemo, useEffect } from 'react';
import { Graphic } from '@/types';
import { useGraphics } from '@/hooks/use-graphics';
import { useAuth } from '@/hooks/use-auth';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { GraphicsTable } from './GraphicsTable';
import { CreateGraphicDialog } from './CreateGraphicDialog';
import { CopyGraphicDialog } from './CopyGraphicDialog';
import { DeleteConfirmDialog } from './DeleteConfirmDialog';
import { Plus, Search, RefreshCw, AlertCircle, Sparkles, Zap, Target, Package, Archive as ArchiveIcon, Trash2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

export function GraphicsTab() {
  const [searchTerm, setSearchTerm] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [copyDialogOpen, setCopyDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [graphicToCopy, setGraphicToCopy] = useState<Graphic | null>(null);
  const [graphicToDelete, setGraphicToDelete] = useState<Graphic | null>(null);
  const [selectedGraphicIds, setSelectedGraphicIds] = useState<number[]>([]);
  
  
  const router = useRouter();
  const {
    graphics,
    loading,
    error,
    refetch,
    createGraphic,
    permanentDeleteGraphic,
    archiveGraphic,
    updateGraphic,
    duplicateGraphic,
  } = useGraphics();
  

  // Ensure graphics is always an array to prevent filter errors
  const safeGraphics = useMemo(
    () => (Array.isArray(graphics) ? graphics : []),
    [graphics],
  );

  const filteredGraphics = useMemo(
    () =>
      safeGraphics.filter(
        graphic =>
          graphic.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
          (graphic.event_name && graphic.event_name.toLowerCase().includes(searchTerm.toLowerCase())),
      ),
    [safeGraphics, searchTerm],
  );

  useEffect(() => {
    setSelectedGraphicIds(prev =>
      prev.filter(id => safeGraphics.some(graphic => graphic.id === id)),
    );
  }, [safeGraphics]);

  const selectedCount = selectedGraphicIds.length;

  const toggleGraphicSelection = useCallback((id: number) => {
    setSelectedGraphicIds(prev =>
      prev.includes(id) ? prev.filter(existingId => existingId !== id) : [...prev, id],
    );
  }, []);

  const toggleSelectAllVisible = useCallback(
    (selectAll: boolean) => {
      const visibleIds = filteredGraphics.map(graphic => graphic.id);
      setSelectedGraphicIds(prev => {
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
    setSelectedGraphicIds([]);
  }, []);

  const handleBulkArchive = useCallback(async () => {
    if (selectedGraphicIds.length === 0) {
      return;
    }

    const idsToArchive = selectedGraphicIds.filter(id =>
      safeGraphics.some(graphic => graphic.id === id),
    );
    if (idsToArchive.length === 0) {
      return;
    }

    const confirmArchive = window.confirm(
      `Archive ${idsToArchive.length} selected graphic${idsToArchive.length === 1 ? '' : 's'}?`,
    );
    if (!confirmArchive) {
      return;
    }

    let successCount = 0;
    for (const id of idsToArchive) {
      // eslint-disable-next-line no-await-in-loop
      const success = await archiveGraphic(id);
      if (success) {
        successCount += 1;
      }
    }

    setSelectedGraphicIds(prev => prev.filter(id => !idsToArchive.includes(id)));

    if (successCount > 0) {
      toast.success(successCount === 1 ? 'Graphic archived' : `${successCount} graphics archived`, {
        description: successCount === 1
          ? 'Selected graphic moved to the archive.'
          : 'Selected graphics moved to the archive.',
      });
    }

    if (successCount !== idsToArchive.length) {
      toast.error('Archive issues', {
        description: `Archived ${successCount} of ${idsToArchive.length} selected graphics.`,
      });
    }
  }, [archiveGraphic, safeGraphics, selectedGraphicIds]);

  const handleBulkDelete = useCallback(async () => {
    if (selectedGraphicIds.length === 0) {
      return;
    }

    const idsToDelete = selectedGraphicIds.filter(id =>
      safeGraphics.some(graphic => graphic.id === id),
    );
    if (idsToDelete.length === 0) {
      return;
    }

    const confirmDelete = window.confirm(
      `Permanently delete ${idsToDelete.length} selected graphic${
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

    setSelectedGraphicIds(prev => prev.filter(id => !idsToDelete.includes(id)));

    if (successCount > 0) {
      toast.success(successCount === 1 ? 'Graphic deleted' : `${successCount} graphics deleted`, {
        description: successCount === 1
          ? 'Selected graphic removed permanently.'
          : 'Selected graphics removed permanently.',
      });
    }

    if (successCount !== idsToDelete.length) {
      toast.error('Delete issues', {
        description: `Deleted ${successCount} of ${idsToDelete.length} selected graphics.`,
      });
    }
  }, [permanentDeleteGraphic, safeGraphics, selectedGraphicIds]);

  const handleCreateGraphic = useCallback(async (data: { title: string; event_name?: string }) => {
    try {
      const canvasData = {
        elements: [],
        settings: {
          width: 1920,
          height: 1080,
          backgroundColor: '#ffffff'
        }
      };
      
      const result = await createGraphic({
        title: data.title,
        event_name: data.event_name,
        data_json: canvasData // Send as object (create endpoint expects dict)
      });
      
      if (result && result.id) {
        toast.success('Graphic created', {
          
          description: `“${result.title}” is ready to edit.`,
        });
        router.push(`/canvas/edit/${result.id}`);
      } else {
        toast.error('Create failed', {
          description: 'A new graphic could not be created. Please try again.',
        });
      }
      
      return !!result;
    } catch (error) {
      console.error('Failed to create graphic:', error);
      toast.error('Create failed', {
        description: 'An unexpected error occurred while creating the graphic.',
      });
      return false;
    }
  }, [createGraphic, router]);

  const handleEditGraphic = useCallback((graphic: Graphic) => {
    router.push(`/canvas/edit/${graphic.id}`);
  }, [router]);

  const handleDuplicateGraphic = useCallback((graphic: Graphic) => {
    setGraphicToCopy(graphic);
    setCopyDialogOpen(true);
  }, []);

  const handleCopyGraphic = useCallback(async (title: string, eventName?: string) => {
    if (!graphicToCopy) return false;
    
    try {
      const result = await duplicateGraphic(graphicToCopy.id, title, eventName);
      if (result) {
        toast.success('Graphic duplicated', {
          
          description: `“${graphicToCopy.title}” copied successfully.`,
        });
        return true;
      }
    } catch (error) {
      console.error('Failed to copy graphic:', error);
      toast.error('Copy failed', {
        
        description: `Unable to copy “${graphicToCopy.title}”. Please try again.`,
        
      });
    }
    return false;
  }, [duplicateGraphic, graphicToCopy]);

  const handleDeleteGraphic = useCallback((graphic: Graphic) => {
    setGraphicToDelete(graphic);
    setDeleteDialogOpen(true);
  }, []);

  const handleConfirmDelete = useCallback(async (): Promise<boolean> => {
    if (!graphicToDelete) return false;
    
    const success = await permanentDeleteGraphic(graphicToDelete.id);
    if (success) {
      setSelectedGraphicIds(prev => prev.filter(id => id !== graphicToDelete.id));
      toast.success('Graphic deleted', {
        
        description: `"${graphicToDelete.title}" has been permanently removed.`,
      });
      setGraphicToDelete(null);
      return true;
    }

    toast.error('Delete failed', {
      
      description: 'Unable to remove the graphic. Please try again.',
      
    });
    return false;
  }, [graphicToDelete, permanentDeleteGraphic]);

  const handleArchiveGraphic = useCallback(async (graphic: Graphic) => {
    try {
      const success = await archiveGraphic(graphic.id);
      if (success) {
        setSelectedGraphicIds(prev => prev.filter(id => id !== graphic.id));
        toast.success('Graphic archived', {
          
          description: `"${graphic.title}" moved to the archive.`,
        });
      }
    } catch (error) {
      console.error('Failed to archive graphic:', error);
      toast.error('Archive failed', {
        
        description: `Unable to archive "${graphic.title}". Please try again.`,
        
      });
    }
  }, [archiveGraphic]);

  const handleViewGraphic = useCallback((graphic: Graphic) => {
    // Open OBS view in new tab
    window.open(`/canvas/view/${graphic.id}`, '_blank');
  }, []);

  if (loading && safeGraphics.length === 0) {
    return (
          <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-6 w-6 animate-spin mr-2" />
        Loading graphics...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 items-center justify-center">
        <div className="flex-1">
          <h2 className="text-3xl font-bold font-abrau gal-text-gradient-peach flex items-center justify-center gap-2">
            Active Graphics
          </h2>
          <p className="text-muted-foreground text-lg text-center">
            Create and manage broadcast graphics for live use
          </p>
        </div>
      </div>

      {/* Search and Actions */}
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Search Input with Icon - Full width on mobile, flex-1 on desktop */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search graphics by title or event name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 border-blue-200 focus:border-blue-400 focus:ring-blue-200"
          />
        </div>
        
        {/* Action Buttons - Same size, aligned */}
        <div className="flex items-center gap-3">
          <Button
            onClick={() => setCreateDialogOpen(true)}
            disabled={loading}
            className="flex items-center gap-2 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 transition-all duration-200 text-white font-semibold"
          >
            <Sparkles className="h-4 w-4" />
            <span>New Graphic</span>
          </Button>
          
          <Button
            variant="outline"
            onClick={refetch}
            disabled={loading}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {safeGraphics.length > 0 && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="ghost"
              onClick={handleClearSelection}
              disabled={selectedCount === 0}
            >
              Clear Selection
            </Button>
            <span className="text-sm text-muted-foreground">
              {selectedCount} selected
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="ghost"
              
              onClick={handleBulkArchive}
              disabled={selectedCount === 0}
              className="flex items-center gap-2 text-amber-600 hover:text-amber-700 hover:bg-amber-50"
            >
              <ArchiveIcon className="h-4 w-4" />
              <span>Archive Selected</span>
            </Button>
            <Button
              variant="ghost"
              
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
        <Card className="border-red-300 bg-gradient-to-r from-red-50 to-orange-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3 text-red-800">
              <AlertCircle className="h-6 w-6 text-red-600" />
              <span className="flex items-center gap-2 font-medium">
                <span className="text-red-500">⚠️</span> {error}
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Graphics Table */}
      {filteredGraphics.length === 0 ? (
        <Card>
          <CardHeader className="text-center py-12">
            <Package className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <CardTitle className="text-lg">
              {searchTerm ? 'No graphics found' : 'No graphics created'}
            </CardTitle>
            <CardDescription>
              {searchTerm 
                ? 'Try different search terms or browse all graphics'
                : 'Active graphics will appear here when they are created'
              }
            </CardDescription>
            {!searchTerm && (
              <Button 
                
                onClick={() => setCreateDialogOpen(true)} 
                className="mt-4"
              >
                <Plus className="h-4 w-4 mr-2" />
                Create Your First Graphic
              </Button>
            )}
          </CardHeader>
        </Card>
      ) : (
        <Card className="border-gray-200">
          <CardContent className="p-0">
            <GraphicsTable
              graphics={filteredGraphics}
              loading={loading}
              onEdit={handleEditGraphic}
              onDuplicate={handleDuplicateGraphic}
              onDelete={handleDeleteGraphic}
              onArchive={handleArchiveGraphic}
              onView={handleViewGraphic}
              selectable
              selectedIds={selectedGraphicIds}
              onToggleSelect={toggleGraphicSelection}
              onToggleSelectAll={toggleSelectAllVisible}
            />
          </CardContent>
        </Card>
      )}

      {/* Create Dialog */}
      <CreateGraphicDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onCreate={handleCreateGraphic}
      />

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
        isArchived={false}
      />
    </div>
  );
}
