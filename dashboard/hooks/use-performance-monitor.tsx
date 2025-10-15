'use client';

import { useEffect, useRef, useState } from 'react';

interface PerformanceMetrics {
  memoryUsage: number;
  renderTime: number;
  componentCount: number;
  intervalCount: number;
  eventListenerCount: number;
}

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
  const listenerRefs = useRef<Set<{element: any, type: string, handler: any}>>(new Set());

  // Track render time
  useEffect(() => {
    renderStart.current = performance.now();
    
    return () => {
      const renderTime = performance.now() - renderStart.current;
      if (renderTime > 16) { // Log slow renders (> 60fps)
        console.warn(`🐌 Slow render in ${componentName}: ${renderTime.toFixed(2)}ms`);
      }
    };
  });

  // Track memory usage (if available)
  useEffect(() => {
    const updateMetrics = () => {
      if ('memory' in performance) {
        const memory = (performance as any).memory;
        const usedMemory = memory.usedJSHeapSize / 1024 / 1024; // MB
        
        setMetrics(prev => ({
          ...prev,
          memoryUsage: usedMemory,
          intervalCount: intervalRefs.current.size,
          eventListenerCount: listenerRefs.current.size,
        }));

        // Warn about high memory usage
        if (usedMemory > 50) { // 50MB threshold
          console.warn(`🔥 High memory usage in ${componentName}: ${usedMemory.toFixed(2)}MB`);
        }
      }
    };

    // Check metrics every 5 seconds
    const interval = setInterval(updateMetrics, 5000);
    return () => clearInterval(interval);
  }, [componentName]);

  // Safe interval creation with tracking
  const createInterval = (callback: () => void, delay: number) => {
    const id = setInterval(callback, delay);
    intervalRefs.current.add(id);
    return id;
  };

  // Safe interval cleanup
  const clearInterval = (id: number) => {
    window.clearInterval(id);
    intervalRefs.current.delete(id);
  };

  // Safe event listener creation with tracking
  const addEventListener = (element: any, type: string, handler: any, options?: any) => {
    const key = { element, type, handler };
    listenerRefs.current.add(key);
    element.addEventListener(type, handler, options);
    return key;
  };

  // Safe event listener cleanup
  const removeEventListener = (element: any, type: string, handler: any) => {
    const key = { element, type, handler };
    listenerRefs.current.delete(key);
    element.removeEventListener(type, handler);
  };

  // Cleanup all intervals and listeners
  useEffect(() => {
    return () => {
      // Clean up intervals
      intervalRefs.current.forEach(id => {
        clearInterval(id);
      });
      intervalRefs.current.clear();

      // Clean up event listeners
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
  }

  getMemoryReport(): string {
    let totalMemory = 0;
    let totalIntervals = 0;
    let totalListeners = 0;

    this.metrics.forEach((metrics, name) => {
      totalMemory += metrics.memoryUsage;
      totalIntervals += metrics.intervalCount;
      totalListeners += metrics.eventListenerCount;
      
      console.log(`📊 ${name}: ${metrics.memoryUsage.toFixed(2)}MB, ${metrics.intervalCount} intervals, ${metrics.eventListenerCount} listeners`);
    });

    return `
🔍 Performance Report:
💾 Total Memory: ${totalMemory.toFixed(2)}MB
⏱️ Total Intervals: ${totalIntervals}
🎧 Total Listeners: ${totalListeners}
📦 Active Components: ${this.metrics.size}
    `;
  }

  checkForLeaks(): void {
    const totalMemory = Array.from(this.metrics.values()).reduce((sum, m) => sum + m.memoryUsage, 0);
    const totalIntervals = Array.from(this.metrics.values()).reduce((sum, m) => sum + m.intervalCount, 0);
    
    if (totalMemory > 100) {
      console.error('🚨 CRITICAL: High memory usage detected!', this.getMemoryReport());
    }
    
    if (totalIntervals > 10) {
      console.warn('⚠️ WARNING: Many intervals running. Potential leak detected.', this.getMemoryReport());
    }
  }
}
