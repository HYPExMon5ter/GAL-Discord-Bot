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

  useEffect(() => {
    fetchGraphics();
  }, [fetchGraphics]);

  return {
    graphics,
    loading,
    error,
    refetch: fetchGraphics,
    createGraphic,
    updateGraphic,
    deleteGraphic,
    archiveGraphic,
  };
}

export function useLocks() {
  const [locks, setLocks] = useState<CanvasLock[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchLocks = useCallback(async () => {
    try {
      setLoading(true);
      const data = await lockApi.getStatus();
      setLocks(data);
    } catch (err) {
      console.error('Error fetching locks:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const acquireLock = useCallback(async (graphicId: number): Promise<CanvasLock | null> => {
    try {
      const lock = await lockApi.acquire(graphicId);
      setLocks(prev => [...prev.filter(l => l.graphic_id !== graphicId), lock]);
      return lock;
    } catch (err) {
      console.error('Error acquiring lock:', err);
      return null;
    }
  }, []);

  const releaseLock = useCallback(async (graphicId: number): Promise<boolean> => {
    try {
      await lockApi.release(graphicId);
      setLocks(prev => prev.filter(l => l.graphic_id !== graphicId));
      return true;
    } catch (err) {
      console.error('Error releasing lock:', err);
      return false;
    }
  }, []);

  const refreshLock = useCallback(async (graphicId: number): Promise<CanvasLock | null> => {
    try {
      const refreshedLock = await lockApi.refresh(graphicId);
      setLocks(prev => 
        prev.map(l => l.graphic_id === graphicId ? refreshedLock : l)
      );
      return refreshedLock;
    } catch (err) {
      console.error('Error refreshing lock:', err);
      return null;
    }
  }, []);

  useEffect(() => {
    fetchLocks();
    const interval = setInterval(fetchLocks, 30000); // Refresh every 30 seconds
    
    return () => clearInterval(interval);
  }, [fetchLocks]);

  return {
    locks,
    loading,
    fetchLocks,
    acquireLock,
    releaseLock,
    refreshLock,
  };
}
