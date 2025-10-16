'use client';

import { useState, useCallback } from 'react';
import { Graphic } from '@/types';
import { useGraphics } from '@/hooks/use-graphics';
import { useLocks } from '@/hooks/use-locks';
import { useAuth } from '@/hooks/use-auth';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { GraphicsTable } from './GraphicsTable';
import { CreateGraphicDialog } from './CreateGraphicDialog';
import { CopyGraphicDialog } from './CopyGraphicDialog';
import { DeleteConfirmDialog } from './DeleteConfirmDialog';
import { Plus, Search, RefreshCw, AlertCircle, Sparkles, Zap, Target, Package } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { useToast } from '@/components/ui/use-toast';

export function GraphicsTab() {
  const [searchTerm, setSearchTerm] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [copyDialogOpen, setCopyDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [graphicToCopy, setGraphicToCopy] = useState<Graphic | null>(null);
  const [graphicToDelete, setGraphicToDelete] = useState<Graphic | null>(null);
  
  const { username } = useAuth();
  const router = useRouter();
  const { graphics, loading, error, refetch, createGraphic, deleteGraphic, permanentDeleteGraphic, archiveGraphic, updateGraphic, duplicateGraphic } = useGraphics();
  const { locks } = useLocks();
  const { toast } = useToast();

  // Ensure graphics is always an array to prevent filter errors
  const safeGraphics = Array.isArray(graphics) ? graphics : [];

  const filteredGraphics = safeGraphics.filter(graphic =>
    graphic.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (graphic.event_name && graphic.event_name.toLowerCase().includes(searchTerm.toLowerCase()))
  );

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
        toast({
          title: 'Graphic created',
          description: `“${result.title}” is ready to edit.`,
        });
        router.push(`/canvas/edit/${result.id}`);
      } else {
        toast({
          title: 'Create failed',
          description: 'A new graphic could not be created. Please try again.',
          variant: 'destructive',
        });
      }
      
      return !!result;
    } catch (error) {
      console.error('Failed to create graphic:', error);
      toast({
        title: 'Create failed',
        description: 'An unexpected error occurred while creating the graphic.',
        variant: 'destructive',
      });
      return false;
    }
  }, [createGraphic, router, toast]);

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
        toast({
          title: 'Graphic duplicated',
          description: `“${graphicToCopy.title}” copied successfully.`,
        });
        return true;
      }
    } catch (error) {
      console.error('Failed to copy graphic:', error);
      toast({
        title: 'Copy failed',
        description: `Unable to copy “${graphicToCopy.title}”. Please try again.`,
        variant: 'destructive',
      });
    }
    return false;
  }, [duplicateGraphic, graphicToCopy, toast]);

  const handleDeleteGraphic = useCallback((graphic: Graphic) => {
    setGraphicToDelete(graphic);
    setDeleteDialogOpen(true);
  }, []);

  const handleConfirmDelete = useCallback(async (): Promise<boolean> => {
    if (!graphicToDelete) return false;
    
    try {
      const success = await permanentDeleteGraphic(graphicToDelete.id);
      if (success) {
        toast({
          title: 'Graphic deleted',
          description: `“${graphicToDelete.title}” has been permanently removed.`,
        });
      }
      return success;
    } catch (error) {
      console.error('Failed to permanently delete graphic:', error);
      toast({
        title: 'Delete failed',
        description: 'Unable to remove the graphic. Please try again.',
        variant: 'destructive',
      });
      return false;
    }
  }, [graphicToDelete, permanentDeleteGraphic, toast]);

  const handleArchiveGraphic = useCallback(async (graphic: Graphic) => {
    try {
      const success = await archiveGraphic(graphic.id);
      if (success) {
        toast({
          title: 'Graphic archived',
          description: `“${graphic.title}” moved to the archive.`,
        });
      }
    } catch (error) {
      console.error('Failed to archive graphic:', error);
      toast({
        title: 'Archive failed',
        description: `Unable to archive “${graphic.title}”. Please try again.`,
        variant: 'destructive',
      });
    }
  }, [archiveGraphic, toast]);

  const handleViewGraphic = useCallback((graphic: Graphic) => {
    // Open OBS view in new tab
    window.open(`/canvas/view/${graphic.id}`, '_blank');
  }, []);

  const getLockForGraphic = (graphicId: number) => {
    return locks.find(lock => lock.graphic_id === graphicId);
  };

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
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent flex items-center gap-2">
            <span className="text-yellow-400">🎨</span> Active Graphics
          </h2>
          <p className="text-muted-foreground text-lg">
            Create and manage broadcast graphics for live use
          </p>
        </div>
        
        <Button 
          size="sm"
          onClick={() => setCreateDialogOpen(true)} 
          className="flex items-center gap-2 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 transition-all duration-200 text-white font-semibold"
        >
          <Sparkles className="h-4 w-4" />
          <span>New Graphic</span>
        </Button>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <Input
            placeholder="Search graphics by title or event name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="border-blue-200 focus:border-blue-400 focus:ring-blue-200"
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
                size="sm"
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
