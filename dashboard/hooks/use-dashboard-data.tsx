'use client';

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  ReactNode,
} from 'react';

import type {
  ArchivedGraphic,
  CanvasLock,
  CreateGraphicRequest,
  Graphic,
  UpdateGraphicRequest,
} from '@/types';
import { archiveApi, graphicsApi, lockApi } from '@/lib/api';

type AsyncFlag = {
  loading: boolean;
  error: string | null;
  hasLoaded: boolean;
};

interface DashboardDataContextValue {
  graphics: Graphic[];
  archivedGraphics: ArchivedGraphic[];
  locks: CanvasLock[];

  graphicsState: AsyncFlag;
  archiveState: AsyncFlag;
  lockState: AsyncFlag;

  fetchGraphics: () => Promise<void>;
  fetchArchive: () => Promise<void>;
  fetchLocks: () => Promise<void>;

  createGraphic: (payload: CreateGraphicRequest) => Promise<Graphic>;
  updateGraphic: (id: number, payload: UpdateGraphicRequest) => Promise<Graphic>;
  duplicateGraphic: (id: number, newTitle?: string, newEventName?: string) => Promise<Graphic>;
  deleteGraphic: (id: number) => Promise<void>;
  archiveGraphic: (id: number) => Promise<void>;
  permanentDeleteGraphic: (id: number) => Promise<void>;

  restoreArchivedGraphic: (id: number) => Promise<void>;
  permanentDeleteArchivedGraphic: (id: number) => Promise<void>;

  getGraphicById: (id: number) => Promise<Graphic | null>;

  acquireLock: (graphicId: number) => Promise<CanvasLock>;
  releaseLock: (graphicId: number) => Promise<void>;
  refreshLock: (graphicId: number) => Promise<CanvasLock>;
  getLockForGraphic: (graphicId: number) => CanvasLock | null;
}

const DashboardDataContext = createContext<DashboardDataContextValue | null>(null);

const INITIAL_ASYNC_FLAG: AsyncFlag = {
  loading: false,
  error: null,
  hasLoaded: false,
};

interface ProviderProps {
  children: ReactNode;
}

export function DashboardDataProvider({ children }: ProviderProps) {
  const [graphics, setGraphics] = useState<Graphic[]>([]);
  const [archivedGraphics, setArchivedGraphics] = useState<ArchivedGraphic[]>([]);
  const [locks, setLocks] = useState<CanvasLock[]>([]);

  const [graphicsState, setGraphicsState] = useState<AsyncFlag>(INITIAL_ASYNC_FLAG);
  const [archiveState, setArchiveState] = useState<AsyncFlag>(INITIAL_ASYNC_FLAG);
  const [lockState, setLockState] = useState<AsyncFlag>(INITIAL_ASYNC_FLAG);

  const fetchGraphics = useCallback(async () => {
    setGraphicsState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const data = await graphicsApi.getAll();
      setGraphics(Array.isArray(data) ? data : []);
      setGraphicsState(prev => ({ ...prev, hasLoaded: true }));
    } catch (error) {
      console.error('Failed to fetch graphics', error);
      setGraphicsState(prev => ({ ...prev, error: 'Failed to fetch graphics' }));
    } finally {
      setGraphicsState(prev => ({ ...prev, loading: false }));
    }
  }, []);

  const fetchArchive = useCallback(async () => {
    setArchiveState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const data = await archiveApi.getAll();
      setArchivedGraphics(Array.isArray(data) ? data : []);
      setArchiveState(prev => ({ ...prev, hasLoaded: true }));
    } catch (error) {
      console.error('Failed to fetch archived graphics', error);
      setArchiveState(prev => ({ ...prev, error: 'Failed to fetch archived graphics' }));
    } finally {
      setArchiveState(prev => ({ ...prev, loading: false }));
    }
  }, []);

  const fetchLocks = useCallback(async () => {
    setLockState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const data = await lockApi.getStatus();
      setLocks(Array.isArray(data) ? data : []);
      setLockState(prev => ({ ...prev, hasLoaded: true }));
    } catch (error) {
      console.error('Failed to fetch locks', error);
      setLockState(prev => ({ ...prev, error: 'Failed to fetch locks' }));
    } finally {
      setLockState(prev => ({ ...prev, loading: false }));
    }
  }, []);

  const createGraphic = useCallback(async (payload: CreateGraphicRequest): Promise<Graphic> => {
    const created = await graphicsApi.create(payload);
    setGraphics(prev => [created, ...prev]);
    return created;
  }, []);

  const updateGraphic = useCallback(async (id: number, payload: UpdateGraphicRequest): Promise<Graphic> => {
    const updated = await graphicsApi.update(id, payload);
    setGraphics(prev => prev.map(graphic => (graphic.id === id ? updated : graphic)));
    return updated;
  }, []);

  const duplicateGraphic = useCallback(async (id: number, newTitle?: string, newEventName?: string): Promise<Graphic> => {
    const duplicated = await graphicsApi.duplicate(id, newTitle, newEventName);
    setGraphics(prev => [duplicated, ...prev]);
    return duplicated;
  }, []);

  const deleteGraphic = useCallback(async (id: number): Promise<void> => {
    await graphicsApi.delete(id);
    setGraphics(prev => prev.filter(graphic => graphic.id !== id));
  }, []);

  const archiveGraphic = useCallback(async (id: number): Promise<void> => {
    await graphicsApi.archive(id);
    setGraphics(prev => prev.filter(graphic => graphic.id !== id));
    fetchArchive().catch(err => {
      console.error('Failed to refresh archive after archive action', err);
    });
  }, [fetchArchive]);

  const permanentDeleteGraphic = useCallback(async (id: number): Promise<void> => {
    await graphicsApi.permanentDelete(id);
    setGraphics(prev => prev.filter(graphic => graphic.id !== id));
    setArchivedGraphics(prev => prev.filter(graphic => graphic.id !== id));
  }, []);

  const restoreArchivedGraphic = useCallback(async (id: number): Promise<void> => {
    await archiveApi.restore(id);
    setArchivedGraphics(prev => prev.filter(graphic => graphic.id !== id));
    fetchGraphics().catch(err => {
      console.error('Failed to refresh graphics after restore', err);
    });
  }, [fetchGraphics]);

  const permanentDeleteArchivedGraphic = useCallback(async (id: number): Promise<void> => {
    await archiveApi.permanentDelete(id);
    setArchivedGraphics(prev => prev.filter(graphic => graphic.id !== id));
  }, []);

  const getGraphicById = useCallback(async (id: number): Promise<Graphic | null> => {
    const existing = graphics.find(graphic => graphic.id === id);
    if (existing) {
      return existing;
    }

    try {
      const graphic = await graphicsApi.getById(id);
      setGraphics(prev => {
        const alreadyPresent = prev.some(item => item.id === graphic.id);
        return alreadyPresent
          ? prev.map(item => (item.id === graphic.id ? graphic : item))
          : [graphic, ...prev];
      });
      return graphic;
    } catch (error) {
      console.error("Failed to fetch graphic", error);
      return null;
    }
  }, [graphics]);

  const acquireLock = useCallback(async (graphicId: number): Promise<CanvasLock> => {
    // Check if we already have a lock for this graphic
    const existingLock = locks.find(lock => lock.graphic_id === graphicId && lock.locked);
    if (existingLock) {
      console.log(`Lock already exists for graphic ${graphicId}, returning existing lock`);
      return existingLock;
    }
    
    const lock = await lockApi.acquire(graphicId);
    setLocks(prev => [...prev.filter(entry => entry.graphic_id !== graphicId), lock]);
    return lock;
  }, [locks]);

  const releaseLock = useCallback(async (graphicId: number): Promise<void> => {
    await lockApi.release(graphicId);
    setLocks(prev => prev.filter(entry => entry.graphic_id !== graphicId));
  }, []);

  const refreshLock = useCallback(async (graphicId: number): Promise<CanvasLock> => {
    const lock = await lockApi.refresh(graphicId);
    setLocks(prev => [...prev.filter(entry => entry.graphic_id !== graphicId), lock]);
    return lock;
  }, []);

  const getLockForGraphic = useCallback((graphicId: number): CanvasLock | null => {
    return locks.find(lock => lock.graphic_id === graphicId) ?? null;
  }, [locks]);

  const value = useMemo<DashboardDataContextValue>(
    () => ({
      graphics,
      archivedGraphics,
      locks,
      graphicsState,
      archiveState,
      lockState,
      fetchGraphics,
      fetchArchive,
      fetchLocks,
      createGraphic,
      updateGraphic,
      duplicateGraphic,
      deleteGraphic,
      archiveGraphic,
      permanentDeleteGraphic,
      restoreArchivedGraphic,
      permanentDeleteArchivedGraphic,
      getGraphicById,
      acquireLock,
      releaseLock,
      refreshLock,
      getLockForGraphic,
    }),
    [
      graphics,
      archivedGraphics,
      locks,
      graphicsState,
      archiveState,
      lockState,
      fetchGraphics,
      fetchArchive,
      fetchLocks,
      createGraphic,
      updateGraphic,
      duplicateGraphic,
      deleteGraphic,
      archiveGraphic,
      permanentDeleteGraphic,
      restoreArchivedGraphic,
      permanentDeleteArchivedGraphic,
      getGraphicById,
      acquireLock,
      releaseLock,
      refreshLock,
      getLockForGraphic,
    ],
  );

  return (
    <DashboardDataContext.Provider value={value}>
      {children}
    </DashboardDataContext.Provider>
  );
}

export function useDashboardData(): DashboardDataContextValue {
  const ctx = useContext(DashboardDataContext);
  if (!ctx) {
    throw new Error('useDashboardData must be used within a DashboardDataProvider');
  }
  return ctx;
}
