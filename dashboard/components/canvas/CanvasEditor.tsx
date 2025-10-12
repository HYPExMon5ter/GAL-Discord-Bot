'use client';

import { useState, useEffect, useCallback } from 'react';
import { Graphic, CanvasLock } from '@/types';
import { useAuth } from '@/hooks/use-auth';
import { useLocks } from '@/hooks/use-locks';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LockBanner } from '@/components/locks/LockBanner';
import { Save, X, RefreshCw, AlertCircle } from 'lucide-react';

interface CanvasEditorProps {
  graphic: Graphic;
  onClose: () => void;
  onSave: (data: { title: string; data_json: string }) => Promise<boolean>;
}

export function CanvasEditor({ graphic, onClose, onSave }: CanvasEditorProps) {
  const { username } = useAuth();
  const { acquireLock, releaseLock, refreshLock } = useLocks();
  
  const [lock, setLock] = useState<CanvasLock | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [title, setTitle] = useState(graphic.title);
  const [canvasData, setCanvasData] = useState<any>(null);

  // Load canvas data
  useEffect(() => {
    try {
      const data = JSON.parse(graphic.data_json || '{}');
      setCanvasData(data);
    } catch (error) {
      console.error('Failed to parse canvas data:', error);
      setCanvasData({
        elements: [],
        settings: {
          width: 1920,
          height: 1080,
          backgroundColor: '#000000'
        }
      });
    }
  }, [graphic.data_json]);

  // Acquire lock on mount
  useEffect(() => {
    const acquireInitialLock = async () => {
      setLoading(true);
      try {
        const acquiredLock = await acquireLock(graphic.id);
        if (acquiredLock) {
          setLock(acquiredLock);
        } else {
          // Could not acquire lock, show message
          console.warn('Could not acquire lock for graphic');
        }
      } catch (error) {
        console.error('Error acquiring lock:', error);
      } finally {
        setLoading(false);
      }
    };

    acquireInitialLock();
  }, [graphic.id, acquireLock]);

  // Auto-refresh lock every 2 minutes
  useEffect(() => {
    if (!lock) return;

    const interval = setInterval(async () => {
      try {
        const refreshedLock = await refreshLock(graphic.id);
        if (refreshedLock) {
          setLock(refreshedLock);
        }
      } catch (error) {
        console.error('Error refreshing lock:', error);
      }
    }, 120000); // 2 minutes

    return () => clearInterval(interval);
  }, [lock, graphic.id, refreshLock]);

  // Release lock on unmount
  useEffect(() => {
    return () => {
      if (lock && lock.user_name === username) {
        releaseLock(graphic.id).catch(console.error);
      }
    };
  }, [lock, graphic.id, username, releaseLock]);

  const handleSave = async () => {
    if (!title.trim()) return;

    setSaving(true);
    try {
      const success = await onSave({
        title: title.trim(),
        data_json: JSON.stringify(canvasData || {})
      });

      if (success) {
        // Release lock and close
        await handleReleaseLock();
        onClose();
      }
    } catch (error) {
      console.error('Error saving graphic:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleReleaseLock = async () => {
    if (lock && lock.user_name === username) {
      try {
        await releaseLock(graphic.id);
        setLock(null);
      } catch (error) {
        console.error('Error releasing lock:', error);
      }
    }
  };

  const handleClose = async () => {
    if (lock && lock.user_name === username) {
      await handleReleaseLock();
    }
    onClose();
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <Card className="w-96">
          <CardContent className="pt-6">
            <div className="flex items-center justify-center gap-3">
              <RefreshCw className="h-6 w-6 animate-spin" />
              <span>Acquiring editing lock...</span>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="border-b p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xl font-bold">Graphic Editor</h3>
            <Button
              variant="outline"
              size="sm"
              onClick={handleClose}
              className="flex items-center gap-1"
            >
              <X className="h-4 w-4" />
              Close Editor
            </Button>
          </div>

          {/* Lock Status */}
          {lock ? (
            <LockBanner
              lock={lock}
              onRefresh={() => window.location.reload()}
              onRelease={handleReleaseLock}
            />
          ) : (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <AlertCircle className="h-5 w-5 text-red-600" />
                <div>
                  <p className="font-medium text-red-800">Cannot Access Editor</p>
                  <p className="text-sm text-red-600">
                    This graphic is currently being edited by another user. Please wait for them to finish or try again later.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Editor Content */}
        <div className="flex-1 overflow-auto">
          <div className="p-6">
            {/* Title Input */}
            <div className="mb-6">
              <label className="block text-sm font-medium mb-2">Graphic Title</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter a descriptive title for this graphic..."
                disabled={!lock || lock.user_name !== username}
              />
            </div>

            {/* Canvas Area - Placeholder */}
            <Card>
              <CardHeader>
                <CardTitle>Design Canvas</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-gray-100 border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
                  <div className="space-y-4">
                    <div className="w-16 h-16 bg-gray-300 rounded-lg mx-auto flex items-center justify-center">
                      <div className="w-8 h-8 bg-gray-400 rounded"></div>
                    </div>
                    <div>
                      <h4 className="font-medium text-gray-700">Canvas Workspace</h4>
                      <p className="text-sm text-gray-500 mt-1">
                        This area will contain the visual design tools for creating broadcast graphics.
                      </p>
                    </div>
                    <div className="text-xs text-gray-400 space-y-1">
                      <p>• Drawing tools and shapes library</p>
                      <p>• Text and typography controls</p>
                      <p>• Layer management system</p>
                      <p>• Real-time preview mode</p>
                      <p>• Animation and transition tools</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Footer */}
        <div className="border-t p-4 bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">
              {lock && lock.user_name === username && (
                <span>Your editing session is active. Changes will be saved automatically.</span>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={handleClose}
                disabled={saving}
              >
                Cancel
              </Button>
              
              <Button
                onClick={handleSave}
                disabled={saving || !lock || lock.user_name !== username || !title.trim()}
                className="flex items-center gap-1"
              >
                <Save className="h-4 w-4" />
                {saving ? 'Saving...' : 'Save & Close'}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
