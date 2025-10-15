'use client';

import { useState, useEffect, useCallback } from 'react';
// import { usePerformanceMonitor } from './use-performance-monitor';
import { CanvasLock } from '@/types';
import { lockApi } from '@/lib/api';

export function useLocks() {
  // const { createInterval, clearInterval } = usePerformanceMonitor('useLocks');
  const [locks, setLocks] = useState<CanvasLock[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch all locks
  const fetchLocks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const locksData = await lockApi.getStatus();
      // Ensure locksData is an array, default to empty array if not
      setLocks(Array.isArray(locksData) ? locksData : []);
    } catch (err) {
      setError('Failed to fetch locks');
      console.error('Failed to fetch locks:', err);
      // Set locks to empty array on error to prevent errors
      setLocks([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Acquire a lock
  const acquireLock = useCallback(async (graphicId: number): Promise<CanvasLock | null> => {
    try {
      const lock = await lockApi.acquire(graphicId);
      setLocks(prev => [...prev.filter(l => l.graphic_id !== graphicId), lock]);
      return lock;
    } catch (err) {
      setError('Failed to acquire lock');
      console.error('Failed to acquire lock:', err);
      return null;
    }
  }, []);

  // Release a lock
  const releaseLock = useCallback(async (graphicId: number): Promise<boolean> => {
    try {
      await lockApi.release(graphicId);
      setLocks(prev => prev.filter(l => l.graphic_id !== graphicId));
      return true;
    } catch (err) {
      setError('Failed to release lock');
      console.error('Failed to release lock:', err);
      return false;
    }
  }, []);

  // Refresh a lock
  const refreshLock = useCallback(async (graphicId: number): Promise<CanvasLock | null> => {
    try {
      const lock = await lockApi.refresh(graphicId);
      setLocks(prev => [...prev.filter(l => l.graphic_id !== graphicId), lock]);
      return lock;
    } catch (err) {
      setError('Failed to refresh lock');
      console.error('Failed to refresh lock:', err);
      return null;
    }
  }, []);

  // Get lock for specific graphic
  const getLockForGraphic = useCallback((graphicId: number): CanvasLock | null => {
    return locks.find(lock => lock.graphic_id === graphicId) || null;
  }, [locks]);

  // Check if graphic is locked by current user
  const isLockedByUser = useCallback((graphicId: number, username: string): boolean => {
    const lock = getLockForGraphic(graphicId);
    return lock?.locked === true && lock?.user_name === username;
  }, [getLockForGraphic]);

  // Check if graphic is locked by another user
  const isLockedByOtherUser = useCallback((graphicId: number, username: string): boolean => {
    const lock = getLockForGraphic(graphicId);
    return lock?.locked === true && lock?.user_name !== username;
  }, [getLockForGraphic]);

  // Auto-refresh locks every 2 minutes (temporarily disabled for debugging)
  useEffect(() => {
    fetchLocks();
    // const interval = createInterval(() => {
    //   setLoading(true);
    //   setError(null);
    //   try {
    //     lockApi.getStatus().then(locksData => {
    //       setLocks(Array.isArray(locksData) ? locksData : []);
    //     }).catch(err => {
    //       setError('Failed to fetch locks');
    //       console.error('Failed to fetch locks:', err);
    //       setLocks([]);
    //     }).finally(() => {
    //       setLoading(false);
    //     });
    //   } catch (err) {
    //     setError('Failed to fetch locks');
    //     console.error('Failed to fetch locks:', err);
    //     setLocks([]);
    //     setLoading(false);
    //   }
    // }, 120000); // 2 minutes instead of 30 seconds
    // return () => clearInterval(interval);
  }, []);

  return {
    locks,
    loading,
    error,
    acquireLock,
    releaseLock,
    refreshLock,
    getLockForGraphic,
    isLockedByUser,
    isLockedByOtherUser,
    fetchLocks,
  };
}
