'use client';

import React, { useState, useCallback, useRef } from 'react';
import { toast } from 'sonner';
import { TopBar } from './TopBar';
import { Sidebar } from './Sidebar';
import { Viewport } from './Viewport';
import { useCanvasState } from '@/hooks/canvas/useCanvasState';
import { useLocks } from '@/hooks/use-locks';
import type { Graphic, BackgroundConfig, CanvasLock } from '@/types';
import type { CanvasElement, ElementType } from '@/lib/canvas/types';

interface CanvasEditorProps {
  graphic: Graphic;
  onClose: () => void;
  onSave: (data: { title: string; event_name: string; data_json: string }) => Promise<boolean>;
}

export function CanvasEditor({ graphic, onClose, onSave }: CanvasEditorProps) {
  
  const { acquireLock, releaseLock, refreshLock } = useLocks();
  
  const [title, setTitle] = useState(graphic.title);
  const [saving, setSaving] = useState(false);
  const [selectedElementId, setSelectedElementId] = useState<string | null>(null);
  const [lock, setLock] = useState<CanvasLock | null>(null);
  const [loading, setLoading] = useState(true);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const lockAcquisitionRef = useRef<boolean>(false);

  // Canvas state management
  const {
    canvas,
    updateBackground,
    addElement,
    updateElement,
    deleteElement,
    getSerializedData,
  } = useCanvasState(graphic.data_json);

  // Acquire lock on mount with guard against double-acquisition
  React.useEffect(() => {
    // Prevent double-acquisition in React Strict Mode
    if (lockAcquisitionRef.current) {
      return;
    }
    lockAcquisitionRef.current = true;

    const acquireInitialLock = async () => {
      try {
        const acquiredLock = await acquireLock(graphic.id);
        if (acquiredLock) {
          setLock(acquiredLock);
        } else {
          toast.error('Graphic in use', {
            description: 'This graphic is currently being edited.',
          });
        }
      } catch (error: any) {
        // Handle 409 errors gracefully (they might be due to our own lock)
        if (error?.response?.status === 409) {
          console.warn('Lock acquisition returned 409, checking if we already have a lock');
          // Try to get the current lock status
          try {
            const response = await fetch(`/api/v1/lock/${graphic.id}/status`, {
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
                'Content-Type': 'application/json',
              },
            });
            if (response.ok) {
              const lockData = await response.json();
              if (lockData.locked && lockData.lock_info) {
                setLock(lockData.lock_info);
                return; // Lock is valid, continue
              }
            }
          } catch (statusError) {
            console.error('Failed to check lock status:', statusError);
          }
        }
        
        console.error('Error acquiring lock:', error);
        toast.error('Lock error', {
          description: 'Could not acquire editing lock.',
        });
      } finally {
        setLoading(false);
      }
    };

    acquireInitialLock();
  }, [graphic.id, acquireLock]);

  // Auto-refresh lock every 2 minutes
  React.useEffect(() => {
    if (!lock) return;

    const interval = window.setInterval(async () => {
      try {
        const refreshedLock = await refreshLock(graphic.id);
        setLock(refreshedLock);
      } catch (error: any) {
        // Handle 404 errors gracefully (lock expired or doesn't exist)
        if (error?.response?.status === 404) {
          console.warn('Lock expired or no longer exists, releasing lock state');
          setLock(null);
          toast.error('Lock expired', {
            description: 'Your editing lock has expired. Please refresh.',
          });
        } else {
          console.error('Error refreshing lock:', error);
          toast.error('Lock refresh failed', {
            description: 'Unable to extend editing lock. Save changes soon.',
          });
        }
      }
    }, 120000);

    return () => window.clearInterval(interval);
  }, [lock, graphic.id, refreshLock]);

  // Release lock on unmount
  React.useEffect(() => {
    return () => {
      if (lock?.locked) {
        releaseLock(graphic.id).catch((error: any) => {
          // Only log error if it's not a 404 (lock already released/expired)
          if (error?.response?.status !== 404) {
            console.error('Error releasing lock:', error);
            toast.error('Lock release error', {
              description: 'Unable to release editing lock.',
            });
          }
          // 404 is expected if lock was already released or expired
        });
      }
    };
  }, [lock?.locked, lock?.id, graphic.id, releaseLock]);

  // Handle background upload
  const handleBackgroundUpload = useCallback((file: File) => {
    const reader = new FileReader();
    reader.onload = (event) => {
      const result = event.target?.result;
      if (typeof result === 'string') {
        const img = new Image();
        img.onload = () => {
          const backgroundConfig: BackgroundConfig = {
            imageUrl: result,
            width: img.naturalWidth,
            height: img.naturalHeight,
          };
          updateBackground(backgroundConfig);
          
          toast.success('Background uploaded', {
            description: 'Canvas resized to match uploaded image.',
          });
        };
        img.onerror = () => {
          toast.error('Upload failed', {
            description: 'Unable to load the selected image file.',
          });
        };
        img.src = result;
      }
    };
    reader.readAsDataURL(file);
  }, [updateBackground]);

  // Handle element addition
  const handleAddElement = useCallback((type: ElementType) => {
    addElement(type);
    setSelectedElementId(null); // Deselect after adding
  }, [addElement]);

  // Handle element selection
  const handleSelectElement = useCallback((elementId: string | null) => {
    setSelectedElementId(elementId);
  }, []);

  // Handle element update
  const handleUpdateElement = useCallback((elementId: string, updates: Partial<CanvasElement>) => {
    updateElement(elementId, updates);
  }, [updateElement]);

  // Handle element deletion
  const handleDeleteElement = useCallback((elementId: string) => {
    deleteElement(elementId);
    if (selectedElementId === elementId) {
      setSelectedElementId(null);
    }
  }, [deleteElement, selectedElementId]);

  // Handle save
  const handleSave = async () => {
    if (!title.trim()) {
      toast.error('Missing title', {
        description: 'Please enter a title before saving.',
      });
      return;
    }

    setSaving(true);
    try {
      const success = await onSave({
        title: title.trim(),
        event_name: graphic.event_name || '',
        data_json: getSerializedData(),
      });

      if (success) {
        toast.success('Graphic saved', {
          description: `"${title.trim()}" has been updated.`,
        });
        onClose();
      } else {
        toast.error('Save failed', {
          description: 'The server did not accept the update. Please try again.',
        });
      }
    } catch (error) {
      console.error('Error saving graphic:', error);
      toast.error('Save failed', {
        description: 'An unexpected error occurred while saving.',
      });
    } finally {
      setSaving(false);
    }
  };

  // Handle close
  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  // Handle title change
  const handleTitleChange = useCallback((newTitle: string) => {
    setTitle(newTitle);
  }, []);

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-background rounded-lg p-6 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p>Acquiring editing lock...</p>
        </div>
      </div>
    );
  }

  const isDisabled = saving || !lock;

  return (
    <div className="fixed inset-0 bg-background z-30 flex flex-col">
      {/* Top Bar */}
      <TopBar
        title={title}
        onTitleChange={handleTitleChange}
        onSave={handleSave}
        onClose={handleClose}
        saving={saving}
        disabled={isDisabled}
      />

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <Sidebar
          elements={canvas.elements}
          selectedElementId={selectedElementId}
          onSelectElement={handleSelectElement}
          onDeleteElement={handleDeleteElement}
          onUpdateElement={handleUpdateElement}
          onAddElement={handleAddElement}
          onBackgroundUpload={handleBackgroundUpload}
          disabled={isDisabled}
        />

        {/* Canvas Viewport */}
        <Viewport
          canvas={canvas}
          selectedElementId={selectedElementId}
          onSelectElement={handleSelectElement}
          onUpdateElement={handleUpdateElement}
          mode="editor"
          disabled={isDisabled}
        />
      </div>

      {/* Hidden file input for background upload */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
      />

  
    </div>
  );
}
