'use client';

import { useEffect } from 'react';

import { useDashboardData } from './use-dashboard-data';

export function useLocks() {
  const {
    locks,
    lockState,
    fetchLocks,
    acquireLock,
    releaseLock,
    refreshLock,
    getLockForGraphic,
  } = useDashboardData();

  useEffect(() => {
    if (!lockState.hasLoaded && !lockState.loading) {
      fetchLocks().catch(error => {
        console.error('Initial lock fetch failed', error);
      });
    }
  }, [fetchLocks, lockState.hasLoaded, lockState.loading]);

  return {
    locks,
    loading: lockState.loading,
    error: lockState.error,
    fetchLocks,
    acquireLock,
    releaseLock,
    refreshLock,
    getLockForGraphic,
    isLockedByUser: (graphicId: number, username: string): boolean => {
      const lock = getLockForGraphic(graphicId);
      return lock?.locked === true;
    },
    isLockedByOtherUser: (graphicId: number, username: string): boolean => {
      const lock = getLockForGraphic(graphicId);
      return lock?.locked === true;
    },
  };
}
