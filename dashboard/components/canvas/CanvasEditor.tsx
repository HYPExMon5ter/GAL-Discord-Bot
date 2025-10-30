'use client';

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { toast } from 'sonner';
import { TopBar } from './TopBar';
import { Sidebar } from './Sidebar';
import { Viewport } from './Viewport';
import { UnsavedChangesDialog } from './UnsavedChangesDialog';
import { LockConflictDialog } from './LockConflictDialog';
import { useCanvasState } from '@/hooks/canvas/useCanvasState';
import { useLocks } from '@/hooks/use-locks';
import type { Graphic, BackgroundConfig, CanvasLock } from '@/types';
import type { CanvasElement, ElementType } from '@/lib/canvas/types';
import { serializeCanvasState } from '@/lib/canvas/serializer';

interface CanvasEditorProps {
  graphic: Graphic;
  onClose: () => void;
  onSave: (data: { title: string; event_name: string; data_json: string }) => Promise<boolean>;
  sessionId: string;
}

export function CanvasEditor({ graphic, onClose, onSave, sessionId }: CanvasEditorProps) {
  
  const { acquireLock, releaseLock, refreshLock } = useLocks();
  
  const [title, setTitle] = useState(graphic.title);
  const [eventName, setEventName] = useState(graphic.event_name || '');
  const [saving, setSaving] = useState(false);
  const [selectedElementId, setSelectedElementId] = useState<string | null>(null);
  const [lock, setLock] = useState<CanvasLock | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [showUnsavedChangesDialog, setShowUnsavedChangesDialog] = useState(false);
  const [showLockConflictDialog, setShowLockConflictDialog] = useState(false);
  const [lockConflictInfo, setLockConflictInfo] = useState<CanvasLock | null>(null);
  const [pendingCloseAction, setPendingCloseAction] = useState<(() => void) | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const lockAcquisitionRef = useRef<boolean>(false);
  const initialCanvasStateRef = useRef<string>('');
  const initialTitleRef = useRef<string>(title);
  const initialEventNameRef = useRef<string>(eventName);

  // Canvas state management
  const {
    canvas,
    updateBackground,
    addElement,
    updateElement,
    deleteElement,
    getSerializedData,
    undo,
    redo,
    canUndo,
    canRedo,
    clearHistory,
  } = useCanvasState(graphic.data_json);

  // Track initial state and changes (FIXED: don't depend on getSerializedData)
  useEffect(() => {
    // Capture initial state only once on mount
    initialCanvasStateRef.current = serializeCanvasState(canvas);
    initialTitleRef.current = title;
    initialEventNameRef.current = eventName;
  }, []); // Empty dependency array - run only once on mount

  // Check for unsaved changes when relevant state changes
  useEffect(() => {
    const currentState = serializeCanvasState(canvas);
    const hasChanges = 
      currentState !== initialCanvasStateRef.current ||
      title !== initialTitleRef.current ||
      eventName !== initialEventNameRef.current;
    setHasUnsavedChanges(hasChanges);
  }, [canvas, title, eventName]); // Track all relevant changes

  // Handle beforeunload event for page navigation protection
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        const message = 'You have unsaved changes. Are you sure you want to leave?';
        e.preventDefault();
        e.returnValue = message;
        return message;
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUnsavedChanges]);

  // Acquire lock on mount with guard against double-acquisition
  React.useEffect(() => {
    // Prevent double-acquisition in React Strict Mode
    if (lockAcquisitionRef.current) {
      return;
    }
    lockAcquisitionRef.current = true;

    const acquireInitialLock = async () => {
      try {
        const acquiredLock = await acquireLock(graphic.id, sessionId);
        if (acquiredLock) {
          setLock(acquiredLock);
        } else {
          toast.error('Graphic in use', {
            description: 'This graphic is currently being edited.',
          });
        }
      } catch (error: any) {
        console.error('Error acquiring lock:', error);
        
        // Handle 409 Conflict errors - another session has the lock
        if (error?.response?.status === 409) {
          const errorMessage = error?.response?.data?.detail || 'Graphic is currently being edited in another session';
          
          // Try to parse the lock info from the error message or fetch it
          try {
            const response = await fetch(`/api/v1/lock/${graphic.id}/status?session_id=${sessionId}`, {
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
                'Content-Type': 'application/json',
              },
            });
            if (response.ok) {
              const lockData = await response.json();
              if (lockData.locked && lockData.lock_info && !lockData.can_edit) {
                setLockConflictInfo(lockData.lock_info);
                setShowLockConflictDialog(true);
                setLoading(false);
                return;
              }
            }
          } catch (statusError) {
            console.error('Failed to check lock status:', statusError);
          }
          
          // Fallback - show generic conflict dialog
          setLockConflictInfo({
            id: 0,
            graphic_id: graphic.id,
            session_id: 'unknown',
            locked: true,
            locked_at: new Date().toISOString(),
            expires_at: new Date(Date.now() + 30 * 60 * 1000).toISOString(), // 30 minutes from now
          });
          setShowLockConflictDialog(true);
          setLoading(false);
          return;
        }
        
        // Handle other errors
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
        const refreshedLock = await refreshLock(graphic.id, sessionId);
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
        releaseLock(graphic.id, sessionId).catch((error: any) => {
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
    if (!title.trim() || !eventName.trim()) {
      toast.error('Missing fields', {
        description: 'Please enter both title and event name before saving.',
      });
      return;
    }

    setSaving(true);
    try {
      const success = await onSave({
        title: title.trim(),
        event_name: eventName.trim(),
        data_json: getSerializedData(),
      });

      if (success) {
        // Reset unsaved changes flag after successful save
        initialCanvasStateRef.current = serializeCanvasState(canvas);
        initialTitleRef.current = title.trim();
        initialEventNameRef.current = eventName.trim();
        setHasUnsavedChanges(false);
        clearHistory();
        
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

  // Handle close with unsaved changes check
  const handleClose = () => {
    if (saving) return;
    
    if (hasUnsavedChanges) {
      setPendingCloseAction(() => () => onClose());
      setShowUnsavedChangesDialog(true);
    } else {
      onClose();
    }
  };

  // Handle save and close from unsaved changes dialog
  const handleSaveAndClose = async () => {
    setShowUnsavedChangesDialog(false);
    await handleSave();
  };

  // Handle discard changes and close
  const handleDiscardAndClose = () => {
    setShowUnsavedChangesDialog(false);
    if (pendingCloseAction) {
      pendingCloseAction();
      setPendingCloseAction(null);
    }
  };

  // Keyboard shortcuts for undo/redo
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+Z for undo (on both Windows and Mac)
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        if (canUndo) {
          undo();
        }
      }
      // Ctrl+Y or Ctrl+Shift+Z for redo
      if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault();
        if (canRedo) {
          redo();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [canUndo, canRedo, undo, redo]);

  // Handle title change
  const handleTitleChange = useCallback((newTitle: string) => {
    setTitle(newTitle);
  }, []);

  // Handle event name change
  const handleEventNameChange = useCallback((newEventName: string) => {
    setEventName(newEventName);
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

  // Handler functions for lock conflict dialog
  const handleCheckLockStatus = async () => {
    try {
      const response = await fetch(`/api/v1/lock/${graphic.id}/status?session_id=${sessionId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const lockData = await response.json();
        if (!lockData.locked || lockData.can_edit) {
          // Lock is available, close dialog and try to acquire it
          setShowLockConflictDialog(false);
          setLockConflictInfo(null);
          acquireInitialLock();
        } else {
          // Update lock info with latest data
          setLockConflictInfo(lockData.lock_info);
          toast.info('Still locked', {
            description: 'The canvas is still being edited in another session.',
          });
        }
      }
    } catch (error) {
      console.error('Failed to check lock status:', error);
      toast.error('Failed to check status');
    }
  };

  const handleForceUnlock = async () => {
    // This would be an admin-only feature - not implemented yet
    toast.error('Not implemented', {
      description: 'Force unlock is not available in this version.',
    });
  };

  const acquireInitialLock = async () => {
    try {
      const acquiredLock = await acquireLock(graphic.id, sessionId);
      if (acquiredLock) {
        setLock(acquiredLock);
        setShowLockConflictDialog(false);
        setLockConflictInfo(null);
      }
    } catch (error: any) {
      console.error('Error acquiring lock:', error);
      // If we still get a conflict, update the dialog with latest info
      if (error?.response?.status === 409) {
        handleCheckLockStatus();
      }
    }
  };

  return (
    <div className="fixed inset-0 bg-background z-30 flex flex-col">
      {/* Top Bar */}
      <TopBar
        title={title}
        eventName={eventName}
        onTitleChange={handleTitleChange}
        onEventNameChange={handleEventNameChange}
        onSave={handleSave}
        onClose={handleClose}
        onUndo={undo}
        onRedo={redo}
        canUndo={canUndo}
        canRedo={canRedo}
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
          onDeleteElement={handleDeleteElement}
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

      {/* Unsaved Changes Dialog */}
      <UnsavedChangesDialog
        open={showUnsavedChangesDialog}
        onOpenChange={setShowUnsavedChangesDialog}
        onDiscard={handleDiscardAndClose}
        onSave={handleSaveAndClose}
        saving={saving}
      />

      {/* Lock Conflict Dialog */}
      {lockConflictInfo && (
        <LockConflictDialog
          isOpen={showLockConflictDialog}
          onOpenChange={setShowLockConflictDialog}
          lock={lockConflictInfo}
          onCheckStatus={handleCheckLockStatus}
          onForceUnlock={handleForceUnlock}
        />
      )}
    </div>
  );
}
