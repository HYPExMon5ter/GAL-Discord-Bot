'use client';

import { useState, useCallback } from 'react';
import { Graphic } from '@/types';
import { useGraphics } from '@/hooks/use-graphics';
import { useLocks } from '@/hooks/use-locks';
import { useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { GraphicCard } from './GraphicCard';
import { CreateGraphicDialog } from './CreateGraphicDialog';
import { CanvasEditor } from '@/components/canvas/CanvasEditor';
import { Plus, Search, RefreshCw, AlertCircle } from 'lucide-react';
import { Input } from '@/components/ui/input';

export function GraphicsTab() {
  const [searchTerm, setSearchTerm] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editingGraphic, setEditingGraphic] = useState<Graphic | null>(null);
  
  const { username } = useAuth();
  const { graphics, loading, error, refetch, createGraphic, deleteGraphic, archiveGraphic, updateGraphic } = useGraphics();
  const { locks } = useLocks();

  // Ensure graphics is always an array to prevent filter errors
  const safeGraphics = Array.isArray(graphics) ? graphics : [];

  const filteredGraphics = safeGraphics.filter(graphic =>
    graphic.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    graphic.created_by.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleCreateGraphic = useCallback(async (data: { title: string }) => {
    try {
      const canvasData = {
        elements: [],
        settings: {
          width: 1920,
          height: 1080,
          backgroundColor: '#000000'
        }
      };
      
      const result = await createGraphic({
        title: data.title,
        data_json: canvasData, // Send as object, not string
        created_by: username || 'Dashboard User' // Add the required created_by field
      });
      return !!result;
    } catch (error) {
      console.error('Failed to create graphic:', error);
      return false;
    }
  }, [createGraphic]);

  const handleEditGraphic = useCallback((graphic: Graphic) => {
    setEditingGraphic(graphic);
  }, []);

  const handleSaveGraphic = useCallback(async (data: { title: string; data_json: string }) => {
    if (!editingGraphic) return false;
    
    try {
      const result = await updateGraphic(editingGraphic.id, data);
      return !!result;
    } catch (error) {
      console.error('Failed to update graphic:', error);
      return false;
    }
  }, [editingGraphic, updateGraphic]);

  const handleDuplicateGraphic = useCallback(async (graphic: Graphic) => {
    try {
      const canvasData = JSON.parse(graphic.data_json || '{}');
      await createGraphic({
        title: `${graphic.title} (Copy)`,
        data_json: JSON.stringify(canvasData)
      });
    } catch (error) {
      console.error('Failed to duplicate graphic:', error);
    }
  }, [createGraphic]);

  const handleDeleteGraphic = useCallback(async (graphic: Graphic) => {
    try {
      await deleteGraphic(graphic.id);
    } catch (error) {
      console.error('Failed to delete graphic:', error);
    }
  }, [deleteGraphic]);

  const handleArchiveGraphic = useCallback(async (graphic: Graphic) => {
    try {
      await archiveGraphic(graphic.id);
    } catch (error) {
      console.error('Failed to archive graphic:', error);
    }
  }, [archiveGraphic]);

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
          <h2 className="text-2xl font-bold">Active Graphics</h2>
          <p className="text-muted-foreground">
            Create and edit broadcast graphics for live use
          </p>
        </div>
        
        <Button onClick={() => setCreateDialogOpen(true)} className="flex items-center gap-2">
          <Plus className="h-4 w-4" />
          New Graphic
        </Button>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search graphics by title or creator..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        
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

      {/* Graphics Grid */}
      {filteredGraphics.length === 0 ? (
        <Card>
          <CardHeader className="text-center py-12">
            <CardTitle className="text-lg">
              {searchTerm ? 'No graphics found' : 'No graphics created yet'}
            </CardTitle>
            <CardDescription>
              {searchTerm 
                ? 'Try different search terms or browse all graphics'
                : 'Get started by creating your first broadcast graphic'
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
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredGraphics.map((graphic) => (
            <GraphicCard
              key={graphic.id}
              graphic={graphic}
              lock={getLockForGraphic(graphic.id)}
              onEdit={handleEditGraphic}
              onDuplicate={handleDuplicateGraphic}
              onDelete={handleDeleteGraphic}
              onArchive={handleArchiveGraphic}
            />
          ))}
        </div>
      )}

      {/* Create Dialog */}
      <CreateGraphicDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onCreate={handleCreateGraphic}
      />

      {/* Canvas Editor */}
      {editingGraphic && (
        <CanvasEditor
          graphic={editingGraphic}
          onClose={() => setEditingGraphic(null)}
          onSave={handleSaveGraphic}
        />
      )}
    </div>
  );
}
