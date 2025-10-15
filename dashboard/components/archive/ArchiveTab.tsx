'use client';

import { useState, useCallback } from 'react';
import { Graphic, ArchivedGraphic } from '@/types';
import { useArchive } from '@/hooks/use-archive';
import { useAuth } from '@/hooks/use-auth';
import { archiveApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { GraphicsTable } from '../graphics/GraphicsTable';
import { CopyGraphicDialog } from '../graphics/CopyGraphicDialog';
import { DeleteConfirmDialog } from '../graphics/DeleteConfirmDialog';
import { Badge } from '@/components/ui/badge';
import { Search, RefreshCw, AlertCircle, Archive, Shield, Copy, Sparkles, Package, Trash2 } from 'lucide-react';
import { Input } from '@/components/ui/input';

export function ArchiveTab() {
  const [searchTerm, setSearchTerm] = useState('');
  const [copyDialogOpen, setCopyDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [graphicToCopy, setGraphicToCopy] = useState<Graphic | ArchivedGraphic | null>(null);
  const [graphicToDelete, setGraphicToDelete] = useState<Graphic | ArchivedGraphic | null>(null);
  
  const { username } = useAuth();
  const { 
    archivedGraphics, 
    loading, 
    error, 
    refetch, 
    restoreGraphic, 
    permanentDeleteGraphic 
  } = useArchive();

  // Simple admin check - in a real app, this would come from the backend
  const isAdmin = username === 'admin' || username === 'blake';

  const filteredGraphics = archivedGraphics.filter(graphic =>
    graphic.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (graphic.event_name && graphic.event_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
    graphic.created_by.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleRestoreGraphic = useCallback(async (graphic: Graphic | ArchivedGraphic) => {
    try {
      const success = await restoreGraphic(graphic.id);
      if (success) {
        // Show success message
        const successMessage = document.createElement('div');
        successMessage.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded z-50';
        successMessage.textContent = `Graphic "${graphic.title}" restored successfully!`;
        document.body.appendChild(successMessage);
        setTimeout(() => {
          document.body.removeChild(successMessage);
        }, 3000);
      }
    } catch (error) {
      console.error('Failed to restore graphic:', error);
      // Show error message
      const errorMessage = document.createElement('div');
      errorMessage.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded z-50';
      errorMessage.textContent = `Failed to restore graphic "${graphic.title}". Please try again.`;
      document.body.appendChild(errorMessage);
      setTimeout(() => {
        document.body.removeChild(errorMessage);
      }, 5000);
    }
  }, [restoreGraphic]);

  const handlePermanentDeleteGraphic = useCallback((graphic: Graphic | ArchivedGraphic) => {
    setGraphicToDelete(graphic);
    setDeleteDialogOpen(true);
  }, []);

  const handleConfirmDelete = useCallback(async (): Promise<boolean> => {
    if (!graphicToDelete) return false;
    
    try {
      const success = await permanentDeleteGraphic(graphicToDelete.id);
      if (success) {
        // Show success message
        const successMessage = document.createElement('div');
        successMessage.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded z-50';
        successMessage.textContent = `Archived graphic "${graphicToDelete.title}" permanently deleted!`;
        document.body.appendChild(successMessage);
        setTimeout(() => {
          document.body.removeChild(successMessage);
        }, 3000);
      }
      return success;
    } catch (error) {
      console.error('Failed to permanently delete archived graphic:', error);
      return false;
    }
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
        // Show success message
        const successMessage = document.createElement('div');
        successMessage.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded z-50';
        successMessage.textContent = `Archived graphic "${graphicToCopy.title}" copied successfully!`;
        document.body.appendChild(successMessage);
        setTimeout(() => {
          document.body.removeChild(successMessage);
        }, 3000);
        return true;
      }
    } catch (error) {
      console.error('Failed to copy archived graphic:', error);
      // Show error message
      const errorMessage = document.createElement('div');
      errorMessage.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded z-50';
      errorMessage.textContent = `Failed to copy archived graphic "${graphicToCopy.title}". Please try again.`;
      document.body.appendChild(errorMessage);
      setTimeout(() => {
        document.body.removeChild(errorMessage);
      }, 5000);
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
        <div>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent flex items-center gap-2">
            <span className="text-orange-400">📦</span> Archived Graphics
          </h2>
          <p className="text-muted-foreground text-lg">
            View and restore previously archived broadcast graphics
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {isAdmin && (
            <Badge variant="secondary" className="flex items-center gap-1 bg-gradient-to-r from-yellow-400 to-orange-500 text-white border-0">
              <Shield className="h-3 w-3" />
              <span className="flex items-center gap-1">
                Admin <span className="text-yellow-200">👑</span>
              </span>
            </Badge>
          )}
          <Badge variant="outline" className="flex items-center gap-1 bg-gradient-to-r from-blue-100 to-purple-100 border-purple-200 text-purple-800">
            <Archive className="h-3 w-3 text-purple-600" />
            <span className="flex items-center gap-1">
              {archivedGraphics.length} Archived <span className="text-purple-400">📚</span>
            </span>
          </Badge>
        </div>
      </div>

      {/* Admin Notice */}
      {isAdmin && (
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3 text-blue-800">
              <Shield className="h-5 w-5 mt-0.5" />
              <div>
                <p className="font-medium">Administrator Access</p>
                <p className="text-sm opacity-75">
                  As an administrator, you can permanently delete archived graphics. 
                  This action cannot be undone and will remove all data permanently.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

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
