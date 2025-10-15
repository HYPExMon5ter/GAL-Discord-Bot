'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Graphic, CanvasLock } from '@/types';
import { useAuth } from '@/hooks/use-auth';
import { useLocks } from '@/hooks/use-locks';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Save,
  ArrowLeft,
  RefreshCw,
  Upload,
  Type,
  Square,
  Circle,
  ChevronLeft,
  ChevronRight,
  Grid3X3,
  Move,
  X,
  User,
  Trophy,
  Medal,
  Undo,
  Redo,
  Settings
} from 'lucide-react';
import { HistoryManager } from '@/lib/history-manager';

interface CanvasEditorProps {
  graphic: Graphic;
  onClose: () => void;
  onSave: (data: { title: string; event_name: string; data_json: string }) => Promise<boolean>;
}

export function CanvasEditor({ graphic, onClose, onSave }: CanvasEditorProps) {
  const { username } = useAuth();
  const { acquireLock, releaseLock, refreshLock } = useLocks();
  
  const [lock, setLock] = useState<CanvasLock | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [title, setTitle] = useState(graphic.title);
  const [eventName, setEventName] = useState(graphic.event_name || '');
  const [canvasData, setCanvasData] = useState<any>(null);
  const [backgroundImage, setBackgroundImage] = useState<string | null>(null);
  const [elements, setElements] = useState<any[]>([]);
  const [selectedElement, setSelectedElement] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState('design');
  
  // Canvas state
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [draggedElement, setDraggedElement] = useState<string | null>(null);
  
  // Grid state
  const [gridVisible, setGridVisible] = useState(true);
  const [gridSnapEnabled, setGridSnapEnabled] = useState(true);
  const gridSize = 20;
  
  // Sidebar state
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  
  // History management
  const historyManagerRef = useRef(new HistoryManager());
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);
  
  // Element snapping
  const [snapToElements, setSnapToElements] = useState(true);
  const [snapLines, setSnapLines] = useState<{x?: number, y?: number}[]>([]);
  
  // Event management
  const [availableEvents, setAvailableEvents] = useState<string[]>([]);
  const [showNewEventInput, setShowNewEventInput] = useState(false);
  const [newEventName, setNewEventName] = useState('');
  
  // Font options
  const fontOptions = [
    { value: 'Arial', label: 'Arial' },
    { value: 'Times New Roman', label: 'Times New Roman' },
    { value: 'Helvetica', label: 'Helvetica' },
    { value: 'Georgia', label: 'Georgia' },
    { value: 'Verdana', label: 'Verdana' }
  ];
  
  const canvasRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load canvas data
  useEffect(() => {
    try {
      let data;
      // data_json should now be a string from the API
      if (typeof graphic.data_json === 'string') {
        data = JSON.parse(graphic.data_json || '{}');
      } else if (typeof graphic.data_json === 'object' && graphic.data_json !== null) {
        data = graphic.data_json || {};
      } else {
        data = {
          elements: [],
          settings: {
            width: 5000,
            height: 5000,
            backgroundColor: '#2a2a2a'
          }
        };
      }
      
      setCanvasData(data);
      setElements(data.elements || []);
      setBackgroundImage(data.backgroundImage || null);
    } catch (error) {
      console.error('Failed to parse canvas data:', error);
      const defaultData = {
        elements: [],
        settings: {
          width: 5000,
          height: 5000,
          backgroundColor: '#2a2a2a'
        }
      };
      setCanvasData(defaultData);
      setElements([]);
      setBackgroundImage(null);
    }
  }, [graphic.data_json]);

  // History management
  useEffect(() => {
    const historyManager = historyManagerRef.current;
    setCanUndo(historyManager.canUndo());
    setCanRedo(historyManager.canRedo());
  }, [elements, canvasData, backgroundImage, zoom, gridVisible, gridSnapEnabled]);
  
  const addToHistory = useCallback((action: any) => {
    historyManagerRef.current.addAction(action);
    setCanUndo(historyManagerRef.current.canUndo());
    setCanRedo(historyManagerRef.current.canRedo());
  }, []);

  // Snap to grid function
  const snapToGrid = useCallback((value: number) => {
    if (!gridSnapEnabled) return value;
    return Math.round(value / gridSize) * gridSize;
  }, [gridSnapEnabled]);

  // Element snapping function
  const snapToElementsFunc = useCallback((element: any, newX: number, newY: number) => {
    if (!snapToElements) return { x: newX, y: newY };
    
    const snapThreshold = gridSize; // 20px
    let snappedX = newX;
    let snappedY = newY;
    const newSnapLines: {x?: number, y?: number}[] = [];
    
    elements.forEach(otherElement => {
      if (otherElement.id === element.id) return;
      
      // Snap to edges
      const otherLeft = otherElement.x;
      const otherRight = otherElement.x + (otherElement.width || 100);
      const otherTop = otherElement.y;
      const otherBottom = otherElement.y + (otherElement.height || 50);
      
      const elemLeft = newX;
      const elemRight = newX + (element.width || 100);
      const elemTop = newY;
      const elemBottom = newY + (element.height || 50);
      
      // Check left edge snap
      if (Math.abs(elemLeft - otherLeft) < snapThreshold) {
        snappedX = otherLeft;
        newSnapLines.push({ x: otherLeft });
      }
      if (Math.abs(elemLeft - otherRight) < snapThreshold) {
        snappedX = otherRight;
        newSnapLines.push({ x: otherRight });
      }
      
      // Check right edge snap
      if (Math.abs(elemRight - otherLeft) < snapThreshold) {
        snappedX = otherLeft - (element.width || 100);
        newSnapLines.push({ x: otherLeft });
      }
      if (Math.abs(elemRight - otherRight) < snapThreshold) {
        snappedX = otherRight - (element.width || 100);
        newSnapLines.push({ x: otherRight });
      }
      
      // Check top edge snap
      if (Math.abs(elemTop - otherTop) < snapThreshold) {
        snappedY = otherTop;
        newSnapLines.push({ y: otherTop });
      }
      if (Math.abs(elemTop - otherBottom) < snapThreshold) {
        snappedY = otherBottom;
        newSnapLines.push({ y: otherBottom });
      }
      
      // Check bottom edge snap
      if (Math.abs(elemBottom - otherTop) < snapThreshold) {
        snappedY = otherTop - (element.height || 50);
        newSnapLines.push({ y: otherTop });
      }
      if (Math.abs(elemBottom - otherBottom) < snapThreshold) {
        snappedY = otherBottom - (element.height || 50);
        newSnapLines.push({ y: otherBottom });
      }
      
      // Check center alignment
      const otherCenterX = otherLeft + (otherElement.width || 100) / 2;
      const otherCenterY = otherTop + (otherElement.height || 50) / 2;
      const elemCenterX = elemLeft + (element.width || 100) / 2;
      const elemCenterY = elemTop + (element.height || 50) / 2;
      
      if (Math.abs(elemCenterX - otherCenterX) < snapThreshold) {
        snappedX = otherCenterX - (element.width || 100) / 2;
        newSnapLines.push({ x: otherCenterX });
      }
      if (Math.abs(elemCenterY - otherCenterY) < snapThreshold) {
        snappedY = otherCenterY - (element.height || 50) / 2;
        newSnapLines.push({ y: otherCenterY });
      }
    });
    
    setSnapLines(newSnapLines);
    return { x: snappedX, y: snappedY };
  }, [snapToElements, gridSize, elements]);

  // Background image upload handler
  const handleBackgroundUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const result = e.target?.result as string;
        const previousBg = backgroundImage;
        
        // Create image element to get dimensions
        const img = new Image();
        img.onload = () => {
          const imageWidth = img.naturalWidth;
          const imageHeight = img.naturalHeight;
          
          // Update canvas size to match image
          const newCanvasData = {
            ...canvasData,
            backgroundImage: result,
            settings: {
              ...canvasData?.settings,
              width: imageWidth,
              height: imageHeight
            }
          };
          
          setBackgroundImage(result);
          setCanvasData(newCanvasData);
          setZoom(1); // Reset zoom to fit the new size
          setPan({ x: 0, y: 0 }); // Reset pan
          
          addToHistory(HistoryManager.createActionTypes.updateBackground(previousBg, result));
          addToHistory(HistoryManager.createActionTypes.updateSettings(
            { settings: canvasData?.settings },
            { settings: newCanvasData.settings },
            'Update canvas size to fit image'
          ));
        };
        img.src = result;
      };
      reader.readAsDataURL(file);
    }
  }, [backgroundImage, canvasData, addToHistory]);

  // Add element handlers
  const addTextElement = useCallback(() => {
    const newElement = {
      id: Date.now().toString(),
      type: 'text',
      content: 'Text',
      x: snapToGrid(100),
      y: snapToGrid(100),
      fontSize: 48,
      fontFamily: 'Arial',
      color: '#000000',
      dataBinding: null
    };
    
    setElements((prev: any[]) => [...prev, newElement]);
    setCanvasData((prev: any) => ({
      ...prev,
      elements: [...(prev?.elements || []), newElement]
    }));
    setSelectedElement(newElement);
    
    addToHistory(HistoryManager.createActionTypes.addElement(newElement));
  }, [snapToGrid, addToHistory]);

  const addPropertyElement = useCallback((propertyType: 'player' | 'score' | 'placement') => {
    const propertyConfig = {
      player: { placeholderText: 'Player Name', defaultWidth: 150, defaultHeight: 40 },
      score: { placeholderText: 'Score', defaultWidth: 100, defaultHeight: 40 },
      placement: { placeholderText: 'Placement', defaultWidth: 120, defaultHeight: 40 }
    };
    
    const config = propertyConfig[propertyType];
    const newElement = {
      id: Date.now().toString(),
      type: propertyType,
      content: config.placeholderText,
      x: snapToGrid(100),
      y: snapToGrid(100),
      width: snapToGrid(config.defaultWidth),
      height: snapToGrid(config.defaultHeight),
      fontSize: 24,
      fontFamily: 'Arial',
      color: '#000000',
      backgroundColor: '#3B82F6',
      dataBinding: {
        source: 'api' as const,
        field: `${propertyType}_name` as const,
        apiEndpoint: null,
        manualValue: null
      },
      isPlaceholder: true
    };
    
    setElements((prev: any[]) => [...prev, newElement]);
    setCanvasData((prev: any) => ({
      ...prev,
      elements: [...(prev?.elements || []), newElement]
    }));
    setSelectedElement(newElement);
    
    addToHistory(HistoryManager.createActionTypes.addElement(newElement));
  }, [snapToGrid, addToHistory]);

  // Removed shape elements - replaced with property elements

  const updateElement = useCallback((elementId: string, updates: Partial<any>) => {
    const currentElement = elements.find(el => el.id === elementId);
    if (!currentElement) return;
    
    // Apply snap to grid for position updates
    let processedUpdates = { ...updates };
    if (updates.x !== undefined) processedUpdates.x = snapToGrid(updates.x);
    if (updates.y !== undefined) processedUpdates.y = snapToGrid(updates.y);
    if (updates.width !== undefined) processedUpdates.width = snapToGrid(updates.width);
    if (updates.height !== undefined) processedUpdates.height = snapToGrid(updates.height);
    
    const updatedElement = { ...currentElement, ...processedUpdates };
    
    setElements((prev: any[]) =>
      prev.map((el: any) => (el.id === elementId ? updatedElement : el))
    );
    setCanvasData((prev: any) => ({
      ...prev,
      elements: (prev?.elements || elements).map((el: any) =>
        el.id === elementId ? updatedElement : el
      )
    }));
    
    addToHistory(HistoryManager.createActionTypes.updateElement(
      elementId, 
      currentElement, 
      updatedElement
    ));
  }, [elements, snapToGrid, addToHistory]);

  const deleteElement = useCallback((elementId: string) => {
    const elementToDelete = elements.find(el => el.id === elementId);
    if (!elementToDelete) return;
    
    setElements((prev: any[]) => prev.filter((el: any) => el.id !== elementId));
    setCanvasData((prev: any) => ({
      ...prev,
      elements: (prev?.elements || elements).filter((el: any) => el.id !== elementId)
    }));
    setSelectedElement(null);
    
    addToHistory(HistoryManager.createActionTypes.deleteElement(elementToDelete));
  }, [elements, addToHistory]);

  // Canvas controls
  const handleZoomIn = useCallback(() => {
    const newZoom = Math.min(zoom * 1.2, 5.0); // 500% max
    setZoom(newZoom);
    addToHistory(HistoryManager.createActionTypes.updateSettings(
      { zoom }, 
      { zoom: newZoom },
      'Zoom in'
    ));
  }, [zoom, addToHistory]);
  
  const handleZoomOut = useCallback(() => {
    const newZoom = Math.max(zoom / 1.2, 0.25); // 25% min
    setZoom(newZoom);
    addToHistory(HistoryManager.createActionTypes.updateSettings(
      { zoom }, 
      { zoom: newZoom },
      'Zoom out'
    ));
  }, [zoom, addToHistory]);
  
  const handleResetZoom = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    addToHistory(HistoryManager.createActionTypes.updateSettings(
      { zoom, pan }, 
      { zoom: 1, pan: { x: 0, y: 0 } },
      'Reset zoom'
    ));
  }, [zoom, pan, addToHistory]);
  
  const handleFitToScreen = useCallback(() => {
    if (canvasRef.current) {
      const container = canvasRef.current.parentElement;
      if (container) {
        const containerWidth = container.clientWidth;
        const containerHeight = container.clientHeight;
        const canvasWidth = canvasData?.settings?.width || 5000;
        const canvasHeight = canvasData?.settings?.height || 5000;
        
        const scaleX = containerWidth / canvasWidth;
        const scaleY = containerHeight / canvasHeight;
        const scale = Math.min(scaleX, scaleY) * 0.9;
        
        const newZoom = Math.max(0.25, Math.min(4.0, scale));
        setZoom(newZoom);
        setPan({ x: 0, y: 0 });
        
        addToHistory(HistoryManager.createActionTypes.updateSettings(
          { zoom, pan }, 
          { zoom: newZoom, pan: { x: 0, y: 0 } },
          'Fit to screen'
        ));
      }
    }
  }, [canvasData, zoom, pan, addToHistory]);

  const toggleGrid = useCallback(() => {
    const newGridVisible = !gridVisible;
    setGridVisible(newGridVisible);
    addToHistory(HistoryManager.createActionTypes.updateSettings(
      { gridVisible }, 
      { gridVisible: newGridVisible },
      newGridVisible ? 'Show grid' : 'Hide grid'
    ));
  }, [gridVisible, addToHistory]);
  
  const toggleSnapToGrid = useCallback(() => {
    const newGridSnapEnabled = !gridSnapEnabled;
    setGridSnapEnabled(newGridSnapEnabled);
    addToHistory(HistoryManager.createActionTypes.updateSettings(
      { gridSnapEnabled }, 
      { gridSnapEnabled: newGridSnapEnabled },
      newGridSnapEnabled ? 'Enable snap to grid' : 'Disable snap to grid'
    ));
  }, [gridSnapEnabled, addToHistory]);

  // Undo/Redo handlers
  const handleUndo = useCallback(() => {
    const action = historyManagerRef.current.undo();
    if (!action) return;
    
    // Apply the inverse of the action
    switch (action.type) {
      case 'add_element':
        setElements((prev: any[]) => prev.filter((el: any) => el.id !== action.data.elementId));
        break;
      case 'update_element':
        setElements((prev: any[]) =>
          prev.map((el: any) => (el.id === action.data.elementId ? action.data.before : el))
        );
        break;
      case 'delete_element':
        setElements((prev: any[]) => [...prev, action.data.before]);
        break;
      case 'update_background':
        setBackgroundImage(action.data.before);
        setCanvasData((prev: any) => ({ ...prev, backgroundImage: action.data.before }));
        break;
      case 'update_settings':
        if (action.data.before.zoom !== undefined) setZoom(action.data.before.zoom);
        if (action.data.before.pan !== undefined) setPan(action.data.before.pan);
        if (action.data.before.gridVisible !== undefined) setGridVisible(action.data.before.gridVisible);
        if (action.data.before.gridSnapEnabled !== undefined) setGridSnapEnabled(action.data.before.gridSnapEnabled);
        break;
    }
    
    setCanUndo(historyManagerRef.current.canUndo());
    setCanRedo(historyManagerRef.current.canRedo());
  }, []);

  const handleRedo = useCallback(() => {
    const action = historyManagerRef.current.redo();
    if (!action) return;
    
    // Apply the action
    switch (action.type) {
      case 'add_element':
        setElements((prev: any[]) => [...prev, action.data.after]);
        break;
      case 'update_element':
        setElements((prev: any[]) =>
          prev.map((el: any) => (el.id === action.data.elementId ? action.data.after : el))
        );
        break;
      case 'delete_element':
        setElements((prev: any[]) => [...prev, action.data.before]);
        break;
      case 'update_background':
        setBackgroundImage(action.data.after);
        setCanvasData((prev: any) => ({ ...prev, backgroundImage: action.data.after }));
        break;
      case 'update_settings':
        if (action.data.after.zoom !== undefined) setZoom(action.data.after.zoom);
        if (action.data.after.pan !== undefined) setPan(action.data.after.pan);
        if (action.data.after.gridVisible !== undefined) setGridVisible(action.data.after.gridVisible);
        if (action.data.after.gridSnapEnabled !== undefined) setGridSnapEnabled(action.data.after.gridSnapEnabled);
        break;
    }
    
    setCanUndo(historyManagerRef.current.canUndo());
    setCanRedo(historyManagerRef.current.canRedo());
  }, []);

  // Mouse wheel zoom
  const handleWheel = useCallback((e: React.WheelEvent) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      const newZoom = Math.max(0.25, Math.min(5.0, zoom * delta));
      setZoom(newZoom);
    }
  }, [zoom]);

  // Pan handlers
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    console.log('Mouse down:', { button: e.button, clientX: e.clientX, clientY: e.clientY });
    
    // Element dragging - check if clicking on an element or its children
    const target = e.target as HTMLElement;
    console.log('Target element:', target.tagName, target.className, target);
    
    const elementElement = target.closest('[data-element-id]');
    console.log('Found element with data-element-id:', elementElement);
    
    if (elementElement) {
      const elementId = elementElement.getAttribute('data-element-id');
      console.log('Element ID from attribute:', elementId);
      
      if (elementId) {
        const element = elements.find(el => el.id === elementId);
        console.log('Found element in state:', element);
        
        if (element) {
          console.log('Starting element drag:', { elementId, elementType: element.type });
          setDraggedElement(elementId);
          setDragStart({ x: e.clientX, y: e.clientY });
          setSelectedElement(element);
          e.preventDefault();
          e.stopPropagation();
          return;
        }
      }
    }
    
    // Canvas panning - if not clicking on an element, enable canvas drag
    // Allow left-click (button 0) for empty area dragging, plus middle/right buttons
    if (e.button === 0 || e.button === 1 || e.button === 2) {
      console.log('Starting canvas pan');
      setIsDragging(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
      e.preventDefault();
    }
  }, [pan, elements]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (draggedElement) {
      // Element dragging
      const element = elements.find(el => el.id === draggedElement);
      if (element) {
        // Calculate raw movement delta
        const deltaX = (e.clientX - dragStart.x) / zoom;
        const deltaY = (e.clientY - dragStart.y) / zoom;
        
        // Calculate new position based on current element position + delta
        const rawNewX = element.x + deltaX;
        const rawNewY = element.y + deltaY;
        
        // Apply snap to grid if enabled
        let newX = snapToGrid(rawNewX);
        let newY = snapToGrid(rawNewY);
        
        // Apply element snapping if enabled
        if (snapToElements) {
          const snapped = snapToElementsFunc(element, newX, newY);
          newX = snapToGrid(snapped.x);
          newY = snapToGrid(snapped.y);
        }
        
        // Constrain to canvas boundaries
        const canvasWidth = canvasData?.settings?.width || 5000;
        const canvasHeight = canvasData?.settings?.height || 5000;
        
        const elementWidth = element.width || (element.type === 'text' ? 100 : 100);
        const elementHeight = element.height || (element.type === 'text' ? 50 : 100);
        
        const constrainedX = Math.max(0, Math.min(newX, canvasWidth - elementWidth));
        const constrainedY = Math.max(0, Math.min(newY, canvasHeight - elementHeight));
        
        // Only update if position actually changed significantly
        const threshold = 1; // Only update if moved by at least 1px
        if (Math.abs(constrainedX - element.x) >= threshold || Math.abs(constrainedY - element.y) >= threshold) {
          updateElement(draggedElement, {
            x: constrainedX,
            y: constrainedY
          });
          
          // Update drag start to the new mouse position to maintain smooth dragging
          setDragStart({ x: e.clientX, y: e.clientY });
        }
      }
    } else if (isDragging) {
      // Canvas panning
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      });
    }
  }, [isDragging, dragStart, zoom, elements, draggedElement, snapToGrid, updateElement, canvasData, snapToElements, snapToElementsFunc]);

  const handleMouseUp = useCallback(() => {
    setDraggedElement(null);
    setIsDragging(false);
    setSnapLines([]); // Clear snap lines when dragging stops
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) {
        if (e.key === 'z' && !e.shiftKey) {
          e.preventDefault();
          handleUndo();
        } else if ((e.key === 'y') || (e.key === 'z' && e.shiftKey)) {
          e.preventDefault();
          handleRedo();
        }
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleUndo, handleRedo]);

  // Acquire lock on mount
  useEffect(() => {
    const acquireInitialLock = async () => {
      setLoading(true);
      try {
        const acquiredLock = await acquireLock(graphic.id);
        if (acquiredLock) {
          setLock(acquiredLock);
        } else {
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
    }, 120000);

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
    if (!title.trim() || !eventName.trim()) {
      console.error('Cannot save: Title or event name is empty');
      return;
    }

    console.log('Starting save process...');
    console.log('Current state:', {
      title: title.trim(),
      eventName: eventName.trim(),
      elementsCount: elements.length,
      hasBackgroundImage: !!backgroundImage,
      canvasSettings: canvasData?.settings
    });
    
    setSaving(true);
    try {
      const updatedCanvasData = {
        ...canvasData,
        elements: elements,
        backgroundImage: backgroundImage,
        settings: {
          ...canvasData?.settings,
          width: canvasData?.settings?.width || 5000,
          height: canvasData?.settings?.height || 5000,
          backgroundColor: canvasData?.settings?.backgroundColor || '#2a2a2a'
        }
      };

      console.log('Saving data:', {
        title: title.trim(),
        data_json_length: JSON.stringify(updatedCanvasData).length,
        elements: elements.length,
        settings: updatedCanvasData.settings
      });

      const success = await onSave({
        title: title.trim(),
        event_name: eventName.trim(),
        data_json: JSON.stringify(updatedCanvasData)
      });

      console.log('Save result:', success);

      if (success) {
        console.log('Save successful, closing...');
        onClose();
      } else {
        console.error('Save failed: onSave returned false');
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

  const handleRefreshLockClick = useCallback(async () => {
    try {
      const refreshedLock = await refreshLock(graphic.id);
      if (refreshedLock) {
        setLock(refreshedLock);
      }
    } catch (error) {
      console.error('Error refreshing lock:', error);
    }
  }, [graphic.id, refreshLock]);

  const handleClose = async () => {
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
    <div className="fixed inset-0 bg-background z-50 flex flex-col">
      <div className="border-b bg-card p-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="sm"
            onClick={handleClose}
            className="flex items-center gap-1"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Button>
          <div className="flex items-center gap-4 flex-1">
            <div className="flex items-center gap-2 flex-1">
              <div className="relative group">
                <Input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="text-lg font-semibold bg-background/50 border border-input/50 rounded-md px-3 py-2 h-10 focus:bg-background focus:border-primary transition-colors"
                  placeholder="Enter graphic title..."
                />
                <div className="absolute -top-6 left-0 text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
                  Click to edit graphic title
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground whitespace-nowrap">Event:</span>
              <div className="relative group min-w-[200px]">
                {showNewEventInput ? (
                  <Input
                    value={newEventName}
                    onChange={(e) => setNewEventName(e.target.value)}
                    onBlur={() => {
                      if (newEventName.trim()) {
                        setEventName(newEventName.trim());
                        if (!availableEvents.includes(newEventName.trim())) {
                          setAvailableEvents([...availableEvents, newEventName.trim()]);
                        }
                      }
                      setShowNewEventInput(false);
                      setNewEventName('');
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.currentTarget.blur();
                      } else if (e.key === 'Escape') {
                        setShowNewEventInput(false);
                        setNewEventName('');
                      }
                    }}
                    className="bg-background/50 border border-input/50 rounded-md px-3 py-2 h-10 text-sm focus:bg-background focus:border-primary transition-colors"
                    placeholder="New event name..."
                    autoFocus
                  />
                ) : (
                  <Select
                    value={eventName}
                    onValueChange={(value) => {
                      if (value === '__create_new__') {
                        setShowNewEventInput(true);
                      } else {
                        setEventName(value);
                      }
                    }}
                  >
                    <SelectTrigger className="bg-background/50 border border-input/50 rounded-md h-10 text-sm hover:bg-background/80 transition-colors">
                      <SelectValue placeholder="Select or create event..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__create_new__">+ Create New Event</SelectItem>
                      {availableEvents.length > 0 && (
                        <>
                          <SelectItem value="" disabled className="text-muted-foreground">──────────</SelectItem>
                          {availableEvents.map((event) => (
                            <SelectItem key={event} value={event}>
                              {event}
                            </SelectItem>
                          ))}
                        </>
                      )}
                    </SelectContent>
                  </Select>
                )}
                <div className="absolute -top-6 left-0 text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                  Click to select or create event
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleUndo}
            disabled={!canUndo}
            className="flex items-center gap-1"
          >
            <Undo className="h-4 w-4" />
            Undo
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRedo}
            disabled={!canRedo}
            className="flex items-center gap-1"
          >
            <Redo className="h-4 w-4" />
            Redo
          </Button>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={saving}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving || !title.trim() || !eventName.trim()}
            className="flex items-center gap-1"
          >
            <Save className="h-4 w-4" />
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        <div className="flex flex-1 overflow-hidden">
          <div className={`${sidebarCollapsed ? 'w-12' : 'w-80'} border-r bg-muted flex flex-col transition-all duration-200`}>
          <div className="p-2 border-b bg-card">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="w-full justify-center"
            >
              {sidebarCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            </Button>
          </div>

          {!sidebarCollapsed && (
            <Tabs value={activeTab} onValueChange={setActiveTab} className="flex h-full flex-col">
              <div className="border-b bg-card px-2">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="design" className="data-[state=active]:bg-blue-600 data-[state=active]:text-white">Design</TabsTrigger>
                  <TabsTrigger value="elements" className="data-[state=active]:bg-blue-600 data-[state=active]:text-white">Elements</TabsTrigger>
                  <TabsTrigger value="data" className="data-[state=active]:bg-blue-600 data-[state=active]:text-white">Data</TabsTrigger>
                </TabsList>
              </div>

              <div className="flex-1 overflow-auto" style={{ paddingBottom: '80px' }}>
                <TabsContent value="design" className="m-0">
                  <div className="p-4 space-y-4">
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Tools</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full justify-start"
                          onClick={() => fileInputRef.current?.click()}
                        >
                          <Upload className="h-4 w-4 mr-2" />
                          Background
                        </Button>
                        <input
                          ref={fileInputRef}
                          type="file"
                          accept="image/*"
                          onChange={handleBackgroundUpload}
                          className="hidden"
                        />
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full justify-start"
                          onClick={addTextElement}
                        >
                          <Type className="h-4 w-4 mr-2" />
                          Add Text
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full justify-start"
                          onClick={() => addPropertyElement('player')}
                        >
                          <User className="h-4 w-4 mr-2" />
                          Player Property
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full justify-start"
                          onClick={() => addPropertyElement('score')}
                        >
                          <Trophy className="h-4 w-4 mr-2" />
                          Score Property
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full justify-start"
                          onClick={() => addPropertyElement('placement')}
                        >
                          <Medal className="h-4 w-4 mr-2" />
                          Placement Property
                        </Button>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Properties</CardTitle>
                      </CardHeader>
                      <CardContent>
                        {selectedElement ? (
                          <div className="space-y-4">
                            <div>
                              <label className="text-xs text-muted-foreground">Type</label>
                              <div className="text-sm font-medium capitalize">{selectedElement.type}</div>
                            </div>

                            {(selectedElement.type === 'text' || ['player', 'score', 'placement'].includes(selectedElement.type)) && (
                              <>
                                <div>
                                  <label className="text-xs text-muted-foreground">Content</label>
                                  <Input
                                    value={selectedElement.content ?? ''}
                                    onChange={(e) =>
                                      updateElement(selectedElement.id, { content: e.target.value })
                                    }
                                    placeholder="Enter text content..."
                                  />
                                </div>
                                <div className="grid grid-cols-2 gap-2">
                                  <div>
                                    <label className="text-xs text-muted-foreground">Font</label>
                                    <Select
                                      value={selectedElement.fontFamily || 'Arial'}
                                      onValueChange={(value) =>
                                        updateElement(selectedElement.id, { fontFamily: value })
                                      }
                                    >
                                      <SelectTrigger className="h-10">
                                        <SelectValue placeholder="Select font..." />
                                      </SelectTrigger>
                                      <SelectContent>
                                        {fontOptions.map((font) => (
                                          <SelectItem key={font.value} value={font.value}>
                                            {font.label}
                                          </SelectItem>
                                        ))}
                                      </SelectContent>
                                    </Select>
                                  </div>
                                  <div>
                                    <label className="text-xs text-muted-foreground">Font Size</label>
                                    <Input
                                      type="number"
                                      min={8}
                                      value={selectedElement.fontSize ?? 16}
                                      onChange={(e) =>
                                        updateElement(selectedElement.id, { fontSize: Number(e.target.value) || 0 })
                                      }
                                    />
                                  </div>
                                </div>
                                <div>
                                  <label className="text-xs text-muted-foreground">Color</label>
                                  <Input
                                    type="color"
                                    value={selectedElement.color ?? '#000000'}
                                    onChange={(e) =>
                                      updateElement(selectedElement.id, { color: e.target.value })
                                    }
                                  />
                                </div>
                              </>
                            )}

                            {['player', 'score', 'placement'].includes(selectedElement.type) && (
                              <>
                                <div>
                                  <label className="text-xs text-muted-foreground">Type</label>
                                  <div className="text-sm font-medium capitalize flex items-center gap-2">
                                    {selectedElement.type === 'player' && <User className="h-4 w-4" />}
                                    {selectedElement.type === 'score' && <Trophy className="h-4 w-4" />}
                                    {selectedElement.type === 'placement' && <Medal className="h-4 w-4" />}
                                    {selectedElement.type} Property
                                  </div>
                                </div>
                                <div>
                                  <label className="text-xs text-muted-foreground">Data Binding</label>
                                  <Select
                                    value={selectedElement.dataBinding?.field || ''}
                                    onValueChange={(value) =>
                                      updateElement(selectedElement.id, {
                                        dataBinding: {
                                          ...selectedElement.dataBinding,
                                          field: value as any
                                        }
                                      })
                                    }
                                  >
                                    <SelectTrigger className="h-10">
                                      <SelectValue placeholder="Select field..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="player_name">Player Name</SelectItem>
                                      <SelectItem value="player_score">Player Score</SelectItem>
                                      <SelectItem value="player_placement">Player Placement</SelectItem>
                                      <SelectItem value="player_rank">Player Rank</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </div>
                              </>
                            )}
                            
                            {selectedElement.type !== 'text' && (
                              <div className="grid grid-cols-2 gap-2">
                                <div>
                                  <label className="text-xs text-muted-foreground">Background</label>
                                  <Input
                                    type="color"
                                    value={selectedElement.backgroundColor === 'rgba(0, 0, 0, 0)' || !selectedElement.backgroundColor ? '#3B82F6' : selectedElement.backgroundColor}
                                    onChange={(e) =>
                                      updateElement(selectedElement.id, { backgroundColor: e.target.value })
                                    }
                                  />
                                </div>
                                <div>
                                  <label className="text-xs text-muted-foreground">Border Color</label>
                                  <Input
                                    type="color"
                                    value={selectedElement.borderColor ?? '#1E40AF'}
                                    onChange={(e) =>
                                      updateElement(selectedElement.id, { borderColor: e.target.value })
                                    }
                                  />
                                </div>
                                <div>
                                  <label className="text-xs text-muted-foreground">Border Width</label>
                                  <Input
                                    type="number"
                                    min={0}
                                    value={selectedElement.borderWidth ?? 2}
                                    onChange={(e) =>
                                      updateElement(selectedElement.id, { borderWidth: Number(e.target.value) || 0 })
                                    }
                                  />
                                </div>
                                <div>
                                  <label className="text-xs text-muted-foreground">Border Radius</label>
                                  <Input
                                    type="number"
                                    min={0}
                                    value={selectedElement.borderRadius ?? 8}
                                    onChange={(e) =>
                                      updateElement(selectedElement.id, { borderRadius: Number(e.target.value) || 0 })
                                    }
                                  />
                                </div>
                              </div>
                            )}

                            <div className="grid grid-cols-2 gap-2">
                              <div>
                                <label className="text-xs text-muted-foreground">X</label>
                                <Input
                                  type="number"
                                  value={selectedElement.x ?? 0}
                                  onChange={(e) =>
                                    updateElement(selectedElement.id, { x: Number(e.target.value) || 0 })
                                  }
                                />
                              </div>
                              <div>
                                <label className="text-xs text-muted-foreground">Y</label>
                                <Input
                                  type="number"
                                  value={selectedElement.y ?? 0}
                                  onChange={(e) =>
                                    updateElement(selectedElement.id, { y: Number(e.target.value) || 0 })
                                  }
                                />
                              </div>
                              <div>
                                <label className="text-xs text-muted-foreground">Width</label>
                                <Input
                                  type="number"
                                  min={0}
                                  value={selectedElement.width ?? 100}
                                  onChange={(e) =>
                                    updateElement(selectedElement.id, { width: Number(e.target.value) || 0 })
                                  }
                                />
                              </div>
                              <div>
                                <label className="text-xs text-muted-foreground">Height</label>
                                <Input
                                  type="number"
                                  min={0}
                                  value={selectedElement.height ?? (selectedElement.type === 'text' ? 50 : 100)}
                                  onChange={(e) =>
                                    updateElement(selectedElement.id, { height: Number(e.target.value) || 0 })
                                  }
                                />
                              </div>
                            </div>

                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => deleteElement(selectedElement.id)}
                              className="w-full"
                            >
                              Delete Element
                            </Button>
                          </div>
                        ) : (
                          <p className="text-sm text-muted-foreground">Select an element to edit properties</p>
                        )}
                      </CardContent>
                    </Card>
                  </div>
                </TabsContent>

                <TabsContent value="elements" className="m-0">
                  <div className="p-4">
                    <Card>
                      <CardHeader>
                        <CardTitle>Element Layers</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          {elements.length === 0 ? (
                            <p className="text-sm text-gray-500">No elements yet. Add some from the Design tab.</p>
                          ) : (
                            elements.map((element, index) => (
                              <div
                                key={element.id}
                                className={`flex items-center justify-between p-3 border rounded cursor-pointer ${
                                  selectedElement?.id === element.id ? 'bg-blue-900/30 border-blue-400' : 'hover:bg-muted/80'
                                }`}
                                onClick={() => setSelectedElement(element)}
                              >
                                <div className="flex items-center gap-3">
                                  <div className="text-sm font-medium">Layer {index + 1}</div>
                                  <div className="text-sm text-gray-500 capitalize truncate max-w-[140px]">
                                    {element.type === 'text' ? element.content : element.type}
                                  </div>
                                </div>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    deleteElement(element.id);
                                  }}
                                  className="h-6 w-6 p-0"
                                >
                                  <X className="h-3 w-3" />
                                </Button>
                              </div>
                            ))
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </TabsContent>

                <TabsContent value="data" className="m-0">
                  <div className="p-4">
                    <Card>
                      <CardHeader>
                        <CardTitle>Data Source</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-4">
                          <div>
                            <label>Bind To</label>
                            <Select disabled={!lock || lock.user_name !== username}>
                              <SelectTrigger className="h-10">
                                <SelectValue placeholder="Select data source..." />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="lobby-specific">Specific Lobby & Round</SelectItem>
                                <SelectItem value="roster">Player Roster</SelectItem>
                                <SelectItem value="tournament">Tournament Data</SelectItem>
                                <SelectItem value="custom">Custom Data</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>

                          {elements.filter((el: any) => el.type === 'text' || ['player', 'score', 'placement'].includes(el.type)).map((element) => (
                            <div key={element.id} className="space-y-2">
                              <div className="text-sm font-medium">{element.content}</div>
                              <Select
                                value={element.dataBinding?.field || ''}
                                onValueChange={(value) =>
                                  updateElement(element.id, { 
                                    dataBinding: { 
                                      ...element.dataBinding, 
                                      field: value 
                                    } 
                                  })
                                }
                              >
                                <SelectTrigger className="h-10">
                                  <SelectValue placeholder="Bind to field..." />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="player_name">Player Name</SelectItem>
                                  <SelectItem value="player_score">Player Score</SelectItem>
                                  <SelectItem value="player_placement">Player Placement</SelectItem>
                                  <SelectItem value="player_rank">Player Rank</SelectItem>
                                  <SelectItem value="team_name">Team Name</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </TabsContent>
              </div>
            </Tabs>
          )}
        </div>

        <div className="flex-1 bg-muted overflow-hidden relative">
          <div
            ref={canvasRef}
            className="absolute inset-0 bg-card overflow-hidden"
            style={{
              backgroundColor: canvasData?.settings?.backgroundColor || '#2a2a2a'
            }}
            onWheel={handleWheel}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
          >
            {gridVisible && (
              <div
                className="absolute inset-0 pointer-events-none"
                style={{
                  backgroundImage: `
                    radial-gradient(circle, rgba(200, 200, 200, 0.4) 1px, transparent 1px)
                  `,
                  backgroundSize: `${gridSize * zoom}px ${gridSize * zoom}px`,
                  backgroundPosition: `${pan.x % (gridSize * zoom)}px ${pan.y % (gridSize * zoom)}px`,
                  zIndex: 1000
                }}
              />
            )}
            
            <div
              style={{
                width: `${(canvasData?.settings?.width || 5000) * zoom}px`,
                height: `${(canvasData?.settings?.height || 5000) * zoom}px`,
                transform: `translate(${pan.x}px, ${pan.y}px)`,
                transformOrigin: 'top left',
                position: 'absolute',
                top: 0,
                left: 0,
                backgroundImage: backgroundImage ? `url(${backgroundImage})` : 'none',
                backgroundSize: `${(canvasData?.settings?.width || 5000) * zoom}px ${(canvasData?.settings?.height || 5000) * zoom}px`,
                backgroundPosition: 'center',
                backgroundColor: canvasData?.settings?.backgroundColor || '#2a2a2a'
              }}
            >
            
            {/* Snap lines */}
            {/* Snap lines */}
            {snapLines.map((line, index) => (
              <div key={index}>
                {line.x !== undefined && (
                  <div
                    className="absolute bg-blue-500 pointer-events-none"
                    style={{
                      left: `${line.x * zoom}px`,
                      top: 0,
                      width: '1px',
                      height: '100%',
                      zIndex: 1001
                    }}
                  />
                )}
                {line.y !== undefined && (
                  <div
                    className="absolute bg-blue-500 pointer-events-none"
                    style={{
                      left: 0,
                      top: `${line.y * zoom}px`,
                      width: '100%',
                      height: '1px',
                      zIndex: 1001
                    }}
                  />
                )}
              </div>
            ))}

            {elements.map((element) => (
              <div
                key={element.id}
                data-element-id={element.id}
                className={`absolute cursor-move ${selectedElement?.id === element.id ? 'ring-2 ring-blue-500' : ''}`}
                style={{
                  left: `${element.x * zoom}px`,
                  top: `${element.y * zoom}px`,
                  width: element.type === 'text' ? 'auto' : `${(element.width || 100) * zoom}px`,
                  height: element.type === 'text' ? 'auto' : `${(element.height || 50) * zoom}px`,
                  zIndex: 1
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedElement(element);
                }}
              >
                {(element.type === 'text' || ['player', 'score', 'placement'].includes(element.type)) && (
                  <div
                    style={{
                      fontSize: `${(element.fontSize || 16) * zoom}px`,
                      color: element.color || '#000000',
                      fontFamily: element.fontFamily || 'Arial',
                      whiteSpace: 'nowrap',
                      backgroundColor: element.backgroundColor || '#3B82F6',
                      padding: `${4 * zoom}px ${8 * zoom}px`,
                      borderRadius: `${4 * zoom}px`
                    }}
                  >
                    {element.content || (element.type === 'text' ? 'Text' : element.placeholderText)}
                  </div>
                )}
              </div>
            ))}
          </div>
          </div>
      </div>
    </div>

      <div className="border-t bg-card p-4">
          <div className="flex items-center justify-between">
            {/* Left side - Grid and Snap controls */}
            <div className="flex items-center gap-2">
              <Button
                variant={gridVisible ? "default" : "outline"}
                size="sm"
                onClick={toggleGrid}
              >
                <Grid3X3 className="h-4 w-4 mr-1" />
                Grid
              </Button>
              <Button
                variant={gridSnapEnabled ? "default" : "outline"}
                size="sm"
                onClick={toggleSnapToGrid}
              >
                <Move className="h-4 w-4 mr-1" />
                Snap
              </Button>
              <Button
                variant={snapToElements ? "default" : "outline"}
                size="sm"
                onClick={() => {
                  const newSnapToElements = !snapToElements;
                  setSnapToElements(newSnapToElements);
                  addToHistory(HistoryManager.createActionTypes.updateSettings(
                    { snapToElements }, 
                    { snapToElements: newSnapToElements },
                    newSnapToElements ? 'Enable snap to elements' : 'Disable snap to elements'
                  ));
                }}
              >
                <Settings className="h-4 w-4 mr-1" />
                Snap Elements
              </Button>
            </div>

            {/* Right side - Zoom controls */}
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleResetZoom}
              >
                Reset
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleFitToScreen}
              >
                Fit
              </Button>
              <div className="flex items-center gap-2 border-l pl-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleZoomOut}
                  disabled={zoom <= 0.25}
                >
                  -
                </Button>
                <span className="text-sm font-medium min-w-[60px] text-center">
                  {Math.round(zoom * 100)}%
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleZoomIn}
                  disabled={zoom >= 5.0}
                >
                  +
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
