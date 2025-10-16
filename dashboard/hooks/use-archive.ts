'use client';

import { useEffect } from 'react';

import { useDashboardData } from './use-dashboard-data';

export function useArchive() {
  const {
    archivedGraphics,
    archiveState,
    fetchArchive,
    restoreArchivedGraphic,
    permanentDeleteArchivedGraphic,
  } = useDashboardData();

  useEffect(() => {
    if (!archiveState.hasLoaded && !archiveState.loading) {
      fetchArchive().catch(error => {
        console.error('Initial archive fetch failed', error);
      });
    }
  }, [archiveState.hasLoaded, archiveState.loading, fetchArchive]);

  return {
    archivedGraphics,
    loading: archiveState.loading,
    error: archiveState.error,
    refetch: fetchArchive,
    restoreGraphic: async (id: number): Promise<boolean> => {
      try {
        await restoreArchivedGraphic(id);
        return true;
      } catch (error) {
        console.error('Failed to restore archived graphic', error);
        return false;
      }
    },
    permanentDeleteGraphic: async (id: number): Promise<boolean> => {
      try {
        await permanentDeleteArchivedGraphic(id);
        return true;
      } catch (error) {
        console.error('Failed to permanently delete archived graphic', error);
        return false;
      }
    },
  };
}
