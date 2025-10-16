'use client';

import { useEffect } from 'react';

import type { CreateGraphicRequest, Graphic, UpdateGraphicRequest } from '@/types';
import { useDashboardData } from './use-dashboard-data';

export function useGraphics() {
  const {
    graphics,
    graphicsState,
    fetchGraphics,
    createGraphic,
    updateGraphic,
    duplicateGraphic,
    deleteGraphic,
    archiveGraphic,
    permanentDeleteGraphic,
    getGraphicById,
  } = useDashboardData();

  useEffect(() => {
    if (!graphicsState.hasLoaded && !graphicsState.loading) {
      fetchGraphics().catch(error => {
        console.error('Initial graphics fetch failed', error);
      });
    }
  }, [fetchGraphics, graphicsState.hasLoaded, graphicsState.loading]);

  return {
    graphics,
    loading: graphicsState.loading,
    error: graphicsState.error,
    refetch: fetchGraphics,
    createGraphic: async (payload: CreateGraphicRequest): Promise<Graphic | null> => {
      try {
        return await createGraphic(payload);
      } catch (error) {
        console.error('Failed to create graphic', error);
        return null;
      }
    },
    updateGraphic: async (id: number, payload: UpdateGraphicRequest): Promise<Graphic | null> => {
      try {
        return await updateGraphic(id, payload);
      } catch (error) {
        console.error('Failed to update graphic', error);
        return null;
      }
    },
    duplicateGraphic: async (id: number, newTitle?: string, newEventName?: string): Promise<Graphic | null> => {
      try {
        return await duplicateGraphic(id, newTitle, newEventName);
      } catch (error) {
        console.error('Failed to duplicate graphic', error);
        return null;
      }
    },
    deleteGraphic: async (id: number): Promise<boolean> => {
      try {
        await deleteGraphic(id);
        return true;
      } catch (error) {
        console.error('Failed to delete graphic', error);
        return false;
      }
    },
    permanentDeleteGraphic: async (id: number): Promise<boolean> => {
      try {
        await permanentDeleteGraphic(id);
        return true;
      } catch (error) {
        console.error('Failed to permanently delete graphic', error);
        return false;
      }
    },
    archiveGraphic: async (id: number): Promise<boolean> => {
      try {
        await archiveGraphic(id);
        return true;
      } catch (error) {
        console.error('Failed to archive graphic', error);
        return false;
      }
    },
    getGraphic: getGraphicById,
  };
}
