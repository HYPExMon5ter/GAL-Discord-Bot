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
import { Plus, Search, RefreshCw, AlertCircle } from 'lucide-react';
import { Input } from '@/components/ui/input';

export function GraphicsTab() {
  const [searchTerm, setSearchTerm] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [copyDialogOpen, setCopyDialogOpen] = useState(false);
  const [graphicToCopy, setGraphicToCopy] = useState<Graphic | null>(null);
  
  const { username } = useAuth();
  const router = useRouter();
  const { graphics, loading, error, refetch, createGraphic, deleteGraphic, archiveGraphic, updateGraphic, duplicateGraphic } = useGraphics();
  const { locks } = useLocks();

  // Ensure graphics is always an array to prevent filter errors
  const safeGraphics = Array.isArray(graphics) ? graphics : [];

  const filteredGraphics = safeGraphics.filter(graphic =>
    graphic.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (graphic.event_name && graphic.event_name.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const handleCreateGraphic = useCallback(async (data: { title: string; event_name?: string }) => {
    try {
      console.log('Creating graphic with data:', data);
      
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
      
      console.log('Create graphic result:', result);
      
      if (result && result.id) {
        console.log('Navigating to canvas editor for graphic ID:', result.id);
        // Navigate to canvas editor after successful creation
        router.push(`/canvas/edit/${result.id}`);
      } else {
        console.error('No result or ID returned from createGraphic');
      }
      
      return !!result;
    } catch (error) {
      console.error('Failed to create graphic:', error);
      return false;
    }
  }, [createGraphic, router]);

  const handleEditGraphic = useCallback((graphic: Graphic) => {
    console.log('Editing graphic:', graphic);
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
        // Show success message
        const successMessage = document.createElement('div');
        successMessage.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded shadow-lg z-50';
        successMessage.textContent = `Graphic "${graphicToCopy.title}" copied successfully!`;
        document.body.appendChild(successMessage);
        setTimeout(() => {
          document.body.removeChild(successMessage);
        }, 3000);
        return true;
      }
    } catch (error) {
      console.error('Failed to copy graphic:', error);
      // Show error message
      const errorMessage = document.createElement('div');
      errorMessage.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded shadow-lg z-50';
      errorMessage.textContent = `Failed to copy graphic "${graphicToCopy.title}". Please try again.`;
      document.body.appendChild(errorMessage);
      setTimeout(() => {
        document.body.removeChild(errorMessage);
      }, 5000);
    }
    return false;
  }, [duplicateGraphic, graphicToCopy]);

  const handleDeleteGraphic = useCallback(async (graphic: Graphic) => {
    try {
      await deleteGraphic(graphic.id);
    } catch (error) {
      console.error('Failed to delete graphic:', error);
    }
  }, [deleteGraphic]);

  const handleArchiveGraphic = useCallback(async (graphic: Graphic) => {
    try {
      const success = await archiveGraphic(graphic.id);
      if (success) {
        // Show success message
        const successMessage = document.createElement('div');
        successMessage.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded shadow-lg z-50';
        successMessage.textContent = `Graphic "${graphic.title}" archived successfully!`;
        document.body.appendChild(successMessage);
        setTimeout(() => {
          document.body.removeChild(successMessage);
        }, 3000);
      }
    } catch (error) {
      console.error('Failed to archive graphic:', error);
      // Show error message
      const errorMessage = document.createElement('div');
      errorMessage.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded shadow-lg z-50';
      errorMessage.textContent = `Failed to archive graphic "${graphic.title}". Please try again.`;
      document.body.appendChild(errorMessage);
      setTimeout(() => {
        document.body.removeChild(errorMessage);
      }, 5000);
    }
  }, [archiveGraphic]);

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
            placeholder="Search graphics by title or event name..."
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

      {/* Graphics Table */}
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
        <Card>
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
    </div>
  );
}
