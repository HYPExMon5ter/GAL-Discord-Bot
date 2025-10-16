'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { logError, logInfo, logWarn } from '@/utils/logging';

interface PerformanceMetrics {
  memoryUsage: number;
  renderTime: number;
  componentCount: number;
  intervalCount: number;
  eventListenerCount: number;
}

type TrackedListener = {
  element: EventTarget;
  type: string;
  handler: EventListenerOrEventListenerObject;
};

export function usePerformanceMonitor(componentName: string) {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    memoryUsage: 0,
    renderTime: 0,
    componentCount: 0,
    intervalCount: 0,
    eventListenerCount: 0,
  });

  const renderStart = useRef<number>(0);
  const intervalRefs = useRef<Set<number>>(new Set());
  const listenerRefs = useRef<Set<TrackedListener>>(new Set());

  // Track render time
  useEffect(() => {
    renderStart.current = performance.now();

    return () => {
      const renderTime = performance.now() - renderStart.current;
      setMetrics(prev => ({ ...prev, renderTime }));
      if (renderTime > 16) {
        logWarn(componentName, `Render completed slowly: ${renderTime.toFixed(2)}ms`);
      }
    };
  });

  // Track memory usage (if available)
  useEffect(() => {
    const updateMetrics = () => {
      if ('memory' in performance) {
        const memory = (performance as { memory: { usedJSHeapSize: number } }).memory;
        const usedMemory = memory.usedJSHeapSize / 1024 / 1024;

        setMetrics(prev => ({
          ...prev,
          memoryUsage: usedMemory,
          intervalCount: intervalRefs.current.size,
          eventListenerCount: listenerRefs.current.size,
        }));

        if (usedMemory > 50) {
          logWarn(componentName, `High memory usage detected: ${usedMemory.toFixed(2)}MB`);
        }
      }
    };

    const interval = window.setInterval(updateMetrics, 5000);
    return () => window.clearInterval(interval);
  }, [componentName]);

  // Safe interval creation with tracking
  const createInterval = useCallback((callback: () => void, delay: number) => {
    const id = window.setInterval(callback, delay);
    intervalRefs.current.add(id);
    return id;
  }, []);

  // Safe interval cleanup
  const clearInterval = useCallback((id: number) => {
    window.clearInterval(id);
    intervalRefs.current.delete(id);
  }, []);

  // Safe event listener creation with tracking
  const addEventListener = useCallback(
    (
      element: EventTarget,
      type: string,
      handler: EventListenerOrEventListenerObject,
      options?: boolean | AddEventListenerOptions,
    ) => {
      const key = { element, type, handler };
      listenerRefs.current.add(key);
      element.addEventListener(type, handler, options);
      return key;
    },
    [],
  );

  // Safe event listener cleanup
  const removeEventListener = useCallback((element: EventTarget, type: string, handler: EventListenerOrEventListenerObject) => {
    const key = { element, type, handler };
    listenerRefs.current.delete(key);
    element.removeEventListener(type, handler);
  }, []);

  // Cleanup all intervals and listeners
  useEffect(() => {
    return () => {
      intervalRefs.current.forEach(id => {
        window.clearInterval(id);
      });
      intervalRefs.current.clear();

      listenerRefs.current.forEach(({ element, type, handler }) => {
        element.removeEventListener(type, handler);
      });
      listenerRefs.current.clear();
    };
  }, []);

  return {
    metrics,
    createInterval,
    clearInterval,
    addEventListener,
    removeEventListener,
  };
}

// Global performance monitor
export class GlobalPerformanceMonitor {
  private static instance: GlobalPerformanceMonitor;
  private metrics: Map<string, PerformanceMetrics> = new Map();
  private intervalCount: number = 0;
  private listenerCount: number = 0;

  static getInstance(): GlobalPerformanceMonitor {
    if (!GlobalPerformanceMonitor.instance) {
      GlobalPerformanceMonitor.instance = new GlobalPerformanceMonitor();
    }
    return GlobalPerformanceMonitor.instance;
  }

  trackComponent(name: string, metrics: PerformanceMetrics) {
    this.metrics.set(name, metrics);
    this.intervalCount += metrics.intervalCount;
    this.listenerCount += metrics.eventListenerCount;
    logInfo(
      name,
      `Tracking component metrics (intervals=${metrics.intervalCount}, listeners=${metrics.eventListenerCount})`,
    );
  }

  getMemoryReport(): string {
    let totalMemory = 0;
    let totalIntervals = 0;
    let totalListeners = 0;

    this.metrics.forEach((metricSet, name) => {
      totalMemory += metricSet.memoryUsage;
      totalIntervals += metricSet.intervalCount;
      totalListeners += metricSet.eventListenerCount;

      logInfo(
        name,
        `Memory ${metricSet.memoryUsage.toFixed(2)}MB | intervals=${metricSet.intervalCount} | listeners=${metricSet.eventListenerCount}`,
      );
    });

    return [
      'Performance Report:',
      `Total Memory: ${totalMemory.toFixed(2)}MB`,
      `Total Intervals: ${totalIntervals}`,
      `Total Listeners: ${totalListeners}`,
      `Active Components: ${this.metrics.size}`,
    ].join('\n');
  }

  checkForLeaks(): void {
    const totalMemory = Array.from(this.metrics.values()).reduce((sum, metricSet) => sum + metricSet.memoryUsage, 0);
    const totalIntervals = Array.from(this.metrics.values()).reduce(
      (sum, metricSet) => sum + metricSet.intervalCount,
      0,
    );

    if (totalMemory > 100) {
      logError('GlobalPerformanceMonitor', 'Critical memory usage detected', this.getMemoryReport());
    }

    if (totalIntervals > 10) {
      logWarn('GlobalPerformanceMonitor', `Many intervals running. Potential leak detected.\n${this.getMemoryReport()}`);
    }
  }
}
