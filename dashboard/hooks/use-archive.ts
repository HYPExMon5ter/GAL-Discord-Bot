'use client';

import { useState, useEffect, useCallback } from 'react';
import { ArchivedGraphic } from '@/types';
import { archiveApi } from '@/lib/api';

export function useArchive() {
  const [archivedGraphics, setArchivedGraphics] = useState<ArchivedGraphic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchArchivedGraphics = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await archiveApi.getAll();
      setArchivedGraphics(data);
    } catch (err) {
      setError('Failed to fetch archived graphics');
      console.error('Error fetching archived graphics:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const restoreGraphic = useCallback(async (id: number): Promise<boolean> => {
    try {
      await archiveApi.restore(id);
      setArchivedGraphics(prev => prev.filter(g => g.id !== id));
      return true;
    } catch (err) {
      setError('Failed to restore graphic');
      console.error('Error restoring graphic:', err);
      return false;
    }
  }, []);

  const permanentDeleteGraphic = useCallback(async (id: number): Promise<boolean> => {
    try {
      await archiveApi.permanentDelete(id);
      setArchivedGraphics(prev => prev.filter(g => g.id !== id));
      return true;
    } catch (err) {
      setError('Failed to permanently delete graphic');
      console.error('Error permanently deleting graphic:', err);
      return false;
    }
  }, []);

  useEffect(() => {
    fetchArchivedGraphics();
  }, [fetchArchivedGraphics]);

  return {
    archivedGraphics,
    loading,
    error,
    refetch: fetchArchivedGraphics,
    restoreGraphic,
    permanentDeleteGraphic,
  };
}
