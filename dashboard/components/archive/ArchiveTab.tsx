'use client';

import { useState, useCallback } from 'react';
import { ArchivedGraphic } from '@/types';
import { useArchive } from '@/hooks/use-archive';
import { useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArchivedGraphicCard } from './ArchivedGraphicCard';
import { Badge } from '@/components/ui/badge';
import { Search, RefreshCw, AlertCircle, Archive, Shield } from 'lucide-react';
import { Input } from '@/components/ui/input';

export function ArchiveTab() {
  const [searchTerm, setSearchTerm] = useState('');
  
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
    graphic.created_by.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleRestoreGraphic = useCallback(async (graphic: ArchivedGraphic) => {
    try {
      await restoreGraphic(graphic.id);
    } catch (error) {
      console.error('Failed to restore graphic:', error);
    }
  }, [restoreGraphic]);

  const handlePermanentDeleteGraphic = useCallback(async (graphic: ArchivedGraphic) => {
    try {
      await permanentDeleteGraphic(graphic.id);
    } catch (error) {
      console.error('Failed to permanently delete graphic:', error);
    }
  }, [permanentDeleteGraphic]);

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
          <h2 className="text-2xl font-bold">Archived Graphics</h2>
          <p className="text-muted-foreground">
            View and restore previously archived broadcast graphics
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          {isAdmin && (
            <Badge variant="secondary" className="flex items-center gap-1">
              <Shield className="h-3 w-3" />
              Admin
            </Badge>
          )}
          <Badge variant="outline" className="flex items-center gap-1">
            <Archive className="h-3 w-3" />
            {archivedGraphics.length} Archived
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

      {/* Archived Graphics Grid */}
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
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredGraphics.map((graphic) => (
            <ArchivedGraphicCard
              key={graphic.id}
              graphic={graphic}
              onRestore={handleRestoreGraphic}
              onPermanentDelete={handlePermanentDeleteGraphic}
              isAdmin={isAdmin}
            />
          ))}
        </div>
      )}

      {/* Archive Stats */}
      {archivedGraphics.length > 0 && (
        <Card className="border-muted">
          <CardHeader>
            <CardTitle className="text-lg">Archive Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold">{archivedGraphics.length}</p>
                <p className="text-sm text-muted-foreground">Total Archived</p>
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {archivedGraphics.filter(g => g.created_by === username).length}
                </p>
                <p className="text-sm text-muted-foreground">Your Graphics</p>
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {new Set(archivedGraphics.map(g => g.created_by)).size}
                </p>
                <p className="text-sm text-muted-foreground">Contributors</p>
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {archivedGraphics.filter(g => 
                    new Date(g.archived_at) > new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
                  ).length}
                </p>
                <p className="text-sm text-muted-foreground">Archived This Week</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
