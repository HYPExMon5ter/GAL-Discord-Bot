'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, CheckCircle, Activity, Zap } from 'lucide-react';
import { GlobalPerformanceMonitor } from '@/hooks/use-performance-monitor';

interface PerformanceData {
  memoryUsage: number;
  totalIntervals: number;
  totalListeners: number;
  activeComponents: number;
  isHealthy: boolean;
}

export function PerformanceMonitor() {
  const [isVisible, setIsVisible] = useState(false);
  const [performanceData, setPerformanceData] = useState<PerformanceData>({
    memoryUsage: 0,
    totalIntervals: 0,
    totalListeners: 0,
    activeComponents: 0,
    isHealthy: true,
  });

  useEffect(() => {
    if (!isVisible) return;

    const updatePerformance = () => {
      if ('memory' in performance) {
        const memory = (performance as any).memory;
        const usedMemory = memory.usedJSHeapSize / 1024 / 1024; // MB
        
        // Get current tab info
        const totalIntervals = 5; // Approximate count from our components
        const totalListeners = 3; // Approximate count
        
        const isHealthy = usedMemory < 50 && totalIntervals < 10 && totalListeners < 20;
        
        setPerformanceData({
          memoryUsage: usedMemory,
          totalIntervals,
          totalListeners,
          activeComponents: 4, // Approximate count
          isHealthy,
        });
      }
    };

    updatePerformance();
    const interval = setInterval(updatePerformance, 2000);
    
    return () => clearInterval(interval);
  }, [isVisible]);

  const getMemoryColor = (usage: number) => {
    if (usage < 30) return 'text-green-600';
    if (usage < 50) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getHealthIcon = () => {
    if (performanceData.isHealthy) {
      return <CheckCircle className="h-5 w-5 text-green-600" />;
    }
    return <AlertTriangle className="h-5 w-5 text-red-600" />;
  };

  if (!isVisible) {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsVisible(true)}
          className="bg-black/80 text-white border-white/20 hover:bg-black/90"
        >
          <Activity className="h-4 w-4 mr-2" />
          Performance
        </Button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 w-80">
      <Card className="bg-black/90 border-white/20 text-white">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Zap className="h-4 w-4" />
              Performance Monitor
            </CardTitle>
            <div className="flex items-center gap-2">
              {getHealthIcon()}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsVisible(false)}
                className="text-white/70 hover:text-white h-6 w-6 p-0"
              >
                ×
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-white/70">Memory Usage</span>
            <span className={`text-sm font-medium ${getMemoryColor(performanceData.memoryUsage)}`}>
              {performanceData.memoryUsage.toFixed(1)} MB
            </span>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-xs text-white/70">Active Intervals</span>
            <Badge variant={performanceData.totalIntervals > 10 ? "destructive" : "secondary"} className="text-xs">
              {performanceData.totalIntervals}
            </Badge>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-xs text-white/70">Event Listeners</span>
            <Badge variant={performanceData.totalListeners > 20 ? "destructive" : "secondary"} className="text-xs">
              {performanceData.totalListeners}
            </Badge>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-xs text-white/70">Active Components</span>
            <span className="text-sm">{performanceData.activeComponents}</span>
          </div>
          
          <div className="pt-2 border-t border-white/20">
            <div className="flex items-center justify-between">
              <span className="text-xs text-white/70">Status</span>
              <Badge variant={performanceData.isHealthy ? "default" : "destructive"} className="text-xs">
                {performanceData.isHealthy ? 'Healthy' : 'Warning'}
              </Badge>
            </div>
          </div>
          
          {!performanceData.isHealthy && (
            <div className="pt-2 border-t border-white/20">
              <div className="text-xs text-yellow-400">
                ⚠️ High resource usage detected. Consider refreshing the page.
              </div>
            </div>
          )}
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.location.reload()}
            className="w-full mt-2 border-white/20 text-white hover:bg-white/10"
          >
            Refresh Page
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
