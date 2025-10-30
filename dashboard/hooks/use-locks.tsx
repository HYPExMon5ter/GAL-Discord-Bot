'use client';

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

  // Note: We no longer fetch all locks on mount since locks are now per-graphic
  // Locks are fetched on-demand when trying to acquire them

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
