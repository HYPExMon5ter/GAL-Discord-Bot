'use client';

import { useState, useEffect, useCallback } from 'react';
import { Graphic, CanvasLock, CreateGraphicRequest, UpdateGraphicRequest } from '@/types';
import { graphicsApi, lockApi } from '@/lib/api';

export function useGraphics() {
  const [graphics, setGraphics] = useState<Graphic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchGraphics = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await graphicsApi.getAll();
      // Ensure data is an array, default to empty array if not
      setGraphics(Array.isArray(data) ? data : []);
    } catch (err) {
      setError('Failed to fetch graphics');
      console.error('Error fetching graphics:', err);
      // Set graphics to empty array on error to prevent filter errors
      setGraphics([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const createGraphic = useCallback(async (data: CreateGraphicRequest): Promise<Graphic | null> => {
    try {
      const newGraphic = await graphicsApi.create(data);
      setGraphics(prev => [newGraphic, ...prev]);
      return newGraphic;
    } catch (err) {
      setError('Failed to create graphic');
      console.error('Error creating graphic:', err);
      return null;
    }
  }, []);

  const updateGraphic = useCallback(async (id: number, data: UpdateGraphicRequest): Promise<Graphic | null> => {
    try {
      const updatedGraphic = await graphicsApi.update(id, data);
      setGraphics(prev => 
        prev.map(g => g.id === id ? updatedGraphic : g)
      );
      return updatedGraphic;
    } catch (err) {
      setError('Failed to update graphic');
      console.error('Error updating graphic:', err);
      return null;
    }
  }, []);

  const duplicateGraphic = useCallback(async (id: number, newTitle?: string, newEventName?: string): Promise<Graphic | null> => {
    try {
      const duplicatedGraphic = await graphicsApi.duplicate(id, newTitle, newEventName);
      setGraphics(prev => [duplicatedGraphic, ...prev]);
      return duplicatedGraphic;
    } catch (err) {
      setError('Failed to duplicate graphic');
      console.error('Error duplicating graphic:', err);
      return null;
    }
  }, []);

  const deleteGraphic = useCallback(async (id: number): Promise<boolean> => {
    try {
      await graphicsApi.delete(id);
      setGraphics(prev => prev.filter(g => g.id !== id));
      return true;
    } catch (err) {
      setError('Failed to delete graphic');
      console.error('Error deleting graphic:', err);
      return false;
    }
  }, []);

  const permanentDeleteGraphic = useCallback(async (id: number): Promise<boolean> => {
    try {
      await graphicsApi.permanentDelete(id);
      setGraphics(prev => prev.filter(g => g.id !== id));
      return true;
    } catch (err) {
      setError('Failed to permanently delete graphic');
      console.error('Error permanently deleting graphic:', err);
      return false;
    }
  }, []);

  const archiveGraphic = useCallback(async (id: number): Promise<boolean> => {
    try {
      await graphicsApi.archive(id);
      setGraphics(prev => prev.filter(g => g.id !== id));
      return true;
    } catch (err) {
      setError('Failed to archive graphic');
      console.error('Error archiving graphic:', err);
      return false;
    }
  }, []);

  const getGraphic = useCallback(async (id: number): Promise<Graphic | null> => {
    try {
      const graphic = await graphicsApi.getById(id);
      return graphic;
    } catch (err) {
      setError('Failed to fetch graphic');
      console.error('Error fetching graphic:', err);
      return null;
    }
  }, []);

  useEffect(() => {
    fetchGraphics();
    
    // Listen for refresh events from canvas editor
    const handleRefresh = () => {
      console.log('Refreshing graphics list after canvas save');
      fetchGraphics();
    };
    
    if (typeof window !== 'undefined') {
      window.addEventListener('refreshGraphics', handleRefresh);
    }
    
    return () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('refreshGraphics', handleRefresh);
      }
    };
  }, [fetchGraphics]);

  return {
    graphics,
    loading,
    error,
    refetch: fetchGraphics,
    createGraphic,
    updateGraphic,
    duplicateGraphic,
    deleteGraphic,
    permanentDeleteGraphic,
    archiveGraphic,
    getGraphic,
  };
}
