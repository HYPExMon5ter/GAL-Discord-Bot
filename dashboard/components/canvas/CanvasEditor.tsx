'use client';

import React, { useState, useCallback, useRef } from 'react';
import { useToast } from '@/components/ui/use-toast';
import { TopBar } from './TopBar';
import { Sidebar } from './Sidebar';
import { Viewport } from './Viewport';
import { useCanvasState } from '@/hooks/canvas/useCanvasState';
import { useLocks } from '@/hooks/use-locks';
import type { Graphic, BackgroundConfig } from '@/types';
import type { CanvasElement, ElementType } from '@/lib/canvas/types';

interface CanvasEditorProps {
  graphic: Graphic;
  onClose: () => void;
  onSave: (data: { title: string; event_name: string; data_json: string }) => Promise<boolean>;
}

export function CanvasEditor({ graphic, onClose, onSave }: CanvasEditorProps) {
  const { toast } = useToast();
  const { acquireLock, releaseLock, refreshLock } = useLocks();
  
  const [title, setTitle] = useState(graphic.title);
  const [saving, setSaving] = useState(false);
  const [selectedElementId, setSelectedElementId] = useState<string | null>(null);
  const [hasLock, setHasLock] = useState(false);
  const [loading, setLoading] = useState(true);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Canvas state management
  const {
    canvas,
    updateBackground,
    addElement,
    updateElement,
    deleteElement,
    getSerializedData,
  } = useCanvasState(graphic.data_json);

  // Acquire lock on mount
  React.useEffect(() => {
    const acquireInitialLock = async () => {
      try {
        const acquiredLock = await acquireLock(graphic.id);
        if (acquiredLock) {
          setHasLock(true);
        } else {
          toast({
            title: 'Lock unavailable',
            description: 'Unable to acquire an editing lock. This graphic may be in use.',
            variant: 'destructive',
          });
        }
      } catch (error) {
        console.error('Error acquiring lock:', error);
        toast({
          title: 'Lock error',
          description: 'We could not acquire the editing lock.',
          variant: 'destructive',
        });
      } finally {
        setLoading(false);
      }
    };

    acquireInitialLock();
  }, [graphic.id, acquireLock, toast]);

  // Auto-refresh lock every 2 minutes
  React.useEffect(() => {
    if (!hasLock) return;

    const interval = window.setInterval(async () => {
      try {
        await refreshLock(graphic.id);
      } catch (error) {
        console.error('Error refreshing lock:', error);
        toast({
          title: 'Lock refresh failed',
          description: 'Unable to extend the editing lock. Save changes soon.',
          variant: 'destructive',
        });
      }
    }, 120000);

    return () => window.clearInterval(interval);
  }, [hasLock, graphic.id, refreshLock, toast]);

  // Release lock on unmount
  React.useEffect(() => {
    return () => {
      if (hasLock) {
        releaseLock(graphic.id).catch((error) => {
          console.error('Error releasing lock:', error);
        });
      }
    };
  }, [lock, graphic.id, releaseLock]);

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
          
          toast({
            title: 'Background uploaded',
            description: 'Canvas resized to match the uploaded image.',
          });
        };
        img.onerror = () => {
          toast({
            title: 'Upload failed',
            description: 'Unable to load the selected image file.',
            variant: 'destructive',
          });
        };
        img.src = result;
      }
    };
    reader.readAsDataURL(file);
  }, [updateBackground, toast]);

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
      toast({
        title: 'Missing title',
        description: 'Please enter a title before saving.',
        variant: 'destructive',
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
        toast({
          title: 'Graphic saved',
          description: `"${title.trim()}" has been updated.`,
        });
        onClose();
      } else {
        toast({
          title: 'Save failed',
          description: 'The server did not accept the update. Please try again.',
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('Error saving graphic:', error);
      toast({
        title: 'Save failed',
        description: 'An unexpected error occurred while saving.',
        variant: 'destructive',
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

  const isDisabled = saving || !hasLock;

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

      {/* Lock Status */}
      {lock && (
        <div className="absolute bottom-4 left-4 bg-background/80 backdrop-blur-sm rounded-lg border px-3 py-2">
          <div className="text-xs text-muted-foreground">
            Editing as {lock.user_name}
          </div>
          <div className="text-xs text-muted-foreground">
            Lock expires: {new Date(lock.expires_at).toLocaleTimeString()}
          </div>
        </div>
      )}
    </div>
  );
}
