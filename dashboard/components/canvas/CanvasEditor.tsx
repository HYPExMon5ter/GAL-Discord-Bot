/**
 * CanvasEditor Component
 * 
 * A comprehensive canvas editing interface for creating and managing graphics.
 * Features include element manipulation, data binding, real-time collaboration,
 * and undo/redo functionality.
 * 
 * Features:
 * - Text and property element creation
 * - Drag-and-drop element positioning
 * - Data binding to tournament datasets
 * - Background image upload
 * - Grid snapping and alignment
 * - Zoom and pan controls
 * - Undo/redo operations
 * - Lock management for collaborative editing
 * 
 * @example
 * ```tsx
 * <CanvasEditor 
 *   graphic={graphicData} 
 *   onClose={() => {}} 
 *   onSave={async (data) => { return true; }}
 * />
 * ```
 */
'use client';

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  Graphic,
  CanvasLock,
  CanvasElement,
  CanvasState,
  CanvasPropertyType,
  SnapLine,
  CanvasDataBinding,
  CanvasBindingSource,
  CanvasBindingField,
  ElementSeries,
  ElementSpacing,
  PlayerData,
  PreviewModeConfig,
  UniversalStyleControls,
  StylePreset,
} from '@/types';
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
import { useToast } from '@/components/ui/use-toast';
import { playerApi } from '@/lib/api';
import {
  createPropertyElement,
  createTextElement,
  deserializeCanvasState,
  updateCanvasElement,
  removeCanvasElement,
  snapValueToGrid,
  clampPositionToCanvas,
  calculateSnapAgainstElements,
  serializeCanvasState,
  updateCanvasBackground,
  updateCanvasSettings,
  DEFAULT_CANVAS_SETTINGS,
  createElementSeries,
  generateElementsFromSeries,
  updateElementSeries,
  deleteElementSeries,
  DEFAULT_ELEMENT_SPACING,
  applyUniversalStylingToElements,
  updatePreviewModeConfig,
  getElementsWithPreviewData,
} from '@/lib/canvas-helpers';
import {
  STYLE_PRESETS,
  FONT_OPTIONS,
  FONT_WEIGHT_OPTIONS,
  TEXT_TRANSFORM_OPTIONS,
  TEXT_ALIGN_OPTIONS,
  getApplicablePresets,
  getPresetById,
  elementStyleToCss,
  validateAndCleanStyle,
  DEFAULT_UNIVERSAL_STYLING,
  getDefaultPreviewModeConfig,
  generateMockPlayerData,
} from '@/lib/canvas-styling';



function getDefaultFieldForElement(element: CanvasElement): CanvasBindingField {
  if (element.type === 'players') return 'player_name';
  if (element.type === 'scores') return 'player_score';
  if (element.type === 'placement') return 'player_placement';
  return 'player_name';
}

function createDefaultBinding(element: CanvasElement): CanvasDataBinding {
  return {
    source: 'series',
    field: getDefaultFieldForElement(element),
    apiEndpoint: null,
    manualValue: element.content ?? '',
    fallbackText: element.placeholderText ?? element.content ?? '',
  };
}

function ensureBinding(element: CanvasElement): CanvasDataBinding {
  const defaultBinding = createDefaultBinding(element);
  const existing = element.dataBinding;

  if (!existing) {
    return defaultBinding;
  }

  return {
    ...defaultBinding,
    ...existing,
  };
}

/**
 * Props interface for the CanvasEditor component
 * @interface CanvasEditorProps
 */
interface CanvasEditorProps {
  /** The graphic object containing canvas data and metadata */
  graphic: Graphic;
  /** Callback function called when the editor should be closed */
  onClose: () => void;
  /** Callback function to save the modified canvas data */
  onSave: (data: { title: string; event_name: string; data_json: string }) => Promise<boolean>;
}

/**
 * CanvasEditor - Main canvas editing component
 * 
 * A comprehensive React component for creating and editing graphics with
 * advanced features including real-time collaboration, data binding,
 * and element manipulation.
 * 
 * @function CanvasEditor
 * @param {CanvasEditorProps} props - Component props
 * @returns {JSX.Element} The rendered canvas editor interface
 * 
 * @example
 * ```tsx
 * <CanvasEditor 
 *   graphic={{
 *     id: 1,
 *     title: "Tournament Graphic",
 *     event_name: "Finals",
 *     data_json: "{}",
 *     created_by: "admin",
 *     created_at: new Date(),
 *     updated_at: new Date(),
 *     archived: false
 *   }}
 *   onClose={() => console.log('Editor closed')}
 *   onSave={async (data) => {
 *     console.log('Saving:', data);
 *     return true;
 *   }}
 * />
 * ```
 * 
 * @features
 * - Canvas element manipulation (text, shapes, images)
 * - Real-time lock management for collaboration
 * - Data binding to tournament datasets
 * - Undo/redo functionality with history management
 * - Grid snapping and alignment tools
 * - Background image upload and management
 * - Zoom and pan controls for navigation
 * - Real-time preview and validation
 * 
 * @state
 * - `lock`: Canvas lock status for collaborative editing
 * - `canvasState`: Current canvas state with elements
 * - `selectedElement`: Currently selected canvas element
 * - `lockTimer`: Timer for lock expiration
 * - `historyStack`: Undo/redo history management
 * 
 * @hooks
 * - `useAuth()`: Authentication context
 * - `useLocks()`: Lock management hooks
 * - `useToast()`: Toast notifications
 * - `useMemo()`: Memoized state calculations
 * - `useCallback()`: Optimized event handlers
 */
export function CanvasEditor({ graphic, onClose, onSave }: CanvasEditorProps) {
  const { username } = useAuth();
  const { acquireLock, releaseLock, refreshLock } = useLocks();
  const { toast } = useToast();

  const initialCanvasState = useMemo<CanvasState>(() => {
    return deserializeCanvasState(graphic.data_json);
  }, [graphic.data_json]);
  
  const [lock, setLock] = useState<CanvasLock | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [title, setTitle] = useState(graphic.title);
  const [eventName, setEventName] = useState(graphic.event_name || '');
  const [canvasData, setCanvasData] = useState<CanvasState>(initialCanvasState);
  const [backgroundImage, setBackgroundImage] = useState<string | null>(
    initialCanvasState.backgroundImage ?? null,
  );
  const [elements, setElements] = useState<CanvasElement[]>(initialCanvasState.elements);
  const [elementSeries, setElementSeries] = useState<ElementSeries[]>(initialCanvasState.elementSeries || []);
  const [selectedElement, setSelectedElement] = useState<CanvasElement | null>(null);
  const [selectedRound, setSelectedRound] = useState<string>('round_1');
  const [activeTab, setActiveTab] = useState('design');
  const canvasSettings = canvasData?.settings ?? DEFAULT_CANVAS_SETTINGS;
  
  // Styling system state
  const [universalStyling, setUniversalStyling] = useState<Partial<UniversalStyleControls>>(DEFAULT_UNIVERSAL_STYLING);
  const [previewConfig, setPreviewConfig] = useState<PreviewModeConfig>(
    initialCanvasState.previewConfig || getDefaultPreviewModeConfig()
  );
  const [selectedPreset, setSelectedPreset] = useState<string>('');
  
  // Real player data state
  const [realPlayerData, setRealPlayerData] = useState<PlayerData[]>([]);
  const [playerDataLoading, setPlayerDataLoading] = useState(false);
  const [playerDataError, setPlayerDataError] = useState<string | null>(null);
  
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
  const [snapLines, setSnapLines] = useState<SnapLine[]>([]);
  
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
    const parsed = deserializeCanvasState(graphic.data_json);
    setCanvasData(parsed);
    setElements(parsed.elements);
    setElementSeries(parsed.elementSeries || []);
    setBackgroundImage(parsed.backgroundImage ?? null);
  }, [graphic.data_json]);

  // History management
  useEffect(() => {
    const historyManager = historyManagerRef.current;
    setCanUndo(historyManager.canUndo());
    setCanRedo(historyManager.canRedo());
  }, [elements, elementSeries, canvasData, backgroundImage, zoom, gridVisible, gridSnapEnabled]);
  
  const addToHistory = useCallback((action: any) => {
    historyManagerRef.current.addAction(action);
    setCanUndo(historyManagerRef.current.canUndo());
    setCanRedo(historyManagerRef.current.canRedo());
  }, []);

  // Snap to grid function
  const snapToGrid = useCallback(
    (value: number) => snapValueToGrid(value, gridSize, gridSnapEnabled),
    [gridSnapEnabled],
  );

  const applyElementSnapping = useCallback(
    (element: CanvasElement, newPosition: { x: number; y: number }) => {
      const { position, lines } = calculateSnapAgainstElements({
        element,
        elements,
        position: newPosition,
        snapToElements,
        gridSize,
      });
      setSnapLines(lines);
      return position;
    },
    [elements, snapToElements, gridSize],
  );

  // Background image upload handler
  const handleBackgroundUpload = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (uploadEvent) => {
        const result = uploadEvent.target?.result;
        if (typeof result !== 'string') {
          toast({
            title: 'Upload failed',
            description: 'Could not read the selected image. Please try again.',
            variant: 'destructive',
          });
          return;
        }

        const previousBackground = backgroundImage;

        const img = new Image();
        img.onload = () => {
          const dimensions = {
            width: img.naturalWidth || DEFAULT_CANVAS_SETTINGS.width,
            height: img.naturalHeight || DEFAULT_CANVAS_SETTINGS.height,
          };

          setCanvasData((prevState) => {
            const updated = updateCanvasBackground(prevState, result, dimensions);

            addToHistory(
              HistoryManager.createActionTypes.updateBackground(previousBackground, result),
            );
            addToHistory(
              HistoryManager.createActionTypes.updateSettings(
                { settings: prevState.settings },
                { settings: updated.settings },
                'Update canvas size to fit image',
              ),
            );

            return updated;
          });

          setBackgroundImage(result);
          setZoom(1);
          setPan({ x: 0, y: 0 });

          toast({
            title: 'Background updated',
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
      };
      reader.onerror = () => {
        toast({
          title: 'Upload failed',
          description: 'Unable to read the selected image file.',
          variant: 'destructive',
        });
      };
      reader.readAsDataURL(file);
    },
    [backgroundImage, addToHistory, toast],
  );

  // Add element handlers
  const addTextElement = useCallback(() => {
    const newElement = createTextElement(snapToGrid);
    setElements((previous) => {
      const nextElements = [...previous, newElement];
      setCanvasData((prevData) => ({
        ...prevData,
        elements: nextElements,
      }));
      return nextElements;
    });
    setSelectedElement(newElement);

    addToHistory(HistoryManager.createActionTypes.addElement(newElement));
  }, [snapToGrid, addToHistory]);

  const addPropertyElement = useCallback((propertyType: CanvasPropertyType) => {
    const newElement = createPropertyElement(propertyType, snapToGrid);
    setElements((previous) => {
      const nextElements = [...previous, newElement];
      setCanvasData((prevData) => ({
        ...prevData,
        elements: nextElements,
      }));
      return nextElements;
    });
    setSelectedElement(newElement);

    addToHistory(HistoryManager.createActionTypes.addElement(newElement));
  }, [snapToGrid, addToHistory]);

  const addScoresElementWithRound = useCallback(() => {
    const newElement = createPropertyElement('scores', snapToGrid);
    // Add round ID to the element series or data binding
    if (newElement.dataBinding) {
      newElement.dataBinding.fallbackText = `Round ${selectedRound}`;
    }
    setElements((previous) => {
      const nextElements = [...previous, newElement];
      setCanvasData((prevData) => ({
        ...prevData,
        elements: nextElements,
      }));
      return nextElements;
    });
    setSelectedElement(newElement);

    addToHistory(HistoryManager.createActionTypes.addElement(newElement));
  }, [snapToGrid, addToHistory, selectedRound]);

  const addElementSeries = useCallback((propertyType: CanvasPropertyType) => {
    const baseElement = createPropertyElement(propertyType, snapToGrid);
    const newSeries = createElementSeries(propertyType, baseElement, DEFAULT_ELEMENT_SPACING);
    
    setElementSeries((previous) => {
      const nextSeries = [...previous, newSeries];
      setCanvasData((prevData) => ({
        ...prevData,
        elementSeries: nextSeries,
      }));
      return nextSeries;
    });
    
    setSelectedElement(baseElement);
    addToHistory(HistoryManager.createActionTypes.addElement(newSeries));
  }, [snapToGrid, addToHistory]);

  const updateElement = useCallback(
    (elementId: string, updates: Partial<CanvasElement>) => {
      const result = updateCanvasElement(elements, elementId, updates, {
        gridSize,
        gridSnapEnabled,
      });

      if (!result) return;

      setElements(result.updatedElements);
      setCanvasData((prevData) => ({
        ...prevData,
        elements: result.updatedElements,
      }));
      setSelectedElement((prev) => (prev?.id === elementId ? result.next : prev));

      addToHistory(
        HistoryManager.createActionTypes.updateElement(
          elementId,
          result.previous,
          result.next,
        ),
      );
    },
    [elements, gridSize, gridSnapEnabled, addToHistory],
  );

  

  // Styling system handlers
  const applyUniversalStyling = useCallback((elementType: CanvasPropertyType) => {
    const updatedElements = applyUniversalStylingToElements(elements, elementType, universalStyling);
    setElements(updatedElements);
    setCanvasData(prevData => ({ ...prevData, elements: updatedElements }));
    
    addToHistory({
      type: 'update_elements',
      data: {
        elementType,
        styling: universalStyling,
        before: elements,
        after: updatedElements
      }
    });

    toast({
      title: 'Styling Applied',
      description: `Universal styling applied to all ${elementType} elements.`,
    });
  }, [elements, universalStyling, addToHistory, toast]);

  const applyStylePreset = useCallback((presetId: string) => {
    const preset = getPresetById(presetId);
    if (!preset) return;

    const updatedElements = elements.map(element => {
      if (preset.applicableTo.includes(element.type as CanvasPropertyType)) {
        return {
          ...element,
          ...preset.style,
        };
      }
      return element;
    });

    setElements(updatedElements);
    setCanvasData(prevData => ({ ...prevData, elements: updatedElements }));
    setSelectedPreset(presetId);
    
    addToHistory({
      type: 'apply_preset',
      data: {
        presetId,
        preset,
        before: elements,
        after: updatedElements
      }
    });

    toast({
      title: 'Preset Applied',
      description: `"${preset.name}" preset applied to applicable elements.`,
    });
  }, [elements, addToHistory, toast]);

  const updateUniversalStyling = useCallback((updates: Partial<UniversalStyleControls>) => {
    const cleanedStyling = validateAndCleanStyle(updates);
    setUniversalStyling(prev => ({ 
      ...prev, 
      ...cleanedStyling 
    } as Partial<UniversalStyleControls>));
  }, []);

  const togglePreviewMode = useCallback(() => {
    const newPreviewConfig = {
      ...previewConfig,
      enabled: !previewConfig.enabled,
    };
    
    setPreviewConfig(newPreviewConfig);
    setCanvasData(prevData => updatePreviewModeConfig(prevData, newPreviewConfig));
    
    addToHistory({
      type: 'toggle_preview',
      data: {
        before: previewConfig,
        after: newPreviewConfig
      }
    });

    toast({
      title: newPreviewConfig.enabled ? 'Preview Mode Enabled' : 'Preview Mode Disabled',
      description: newPreviewConfig.enabled 
        ? 'Viewing canvas with mock data and auto-generated elements.'
        : 'Returned to design mode.',
    });
  }, [previewConfig, addToHistory, toast]);

  const updatePreviewConfig = useCallback((updates: Partial<PreviewModeConfig>) => {
    const newPreviewConfig = { ...previewConfig, ...updates };
    setPreviewConfig(newPreviewConfig);
    setCanvasData(prevData => updatePreviewModeConfig(prevData, newPreviewConfig));
  }, [previewConfig]);

  // Real player data fetching
  const fetchRealPlayerData = useCallback(async () => {
    setPlayerDataLoading(true);
    setPlayerDataError(null);
    
    try {
      const response = await playerApi.getRankedPlayers({
        sortBy: previewConfig.sortBy,
        sortOrder: previewConfig.sortOrder,
        limit: previewConfig.playerCount || 50,
      });
      
      const playerData: PlayerData[] = response.players.map(player => ({
        player_name: player.player_name,
        total_points: player.total_points,
        standing_rank: player.standing_rank,
        player_id: player.player_id,
        discord_id: player.discord_id,
        riot_id: player.riot_id,
        round_scores: player.round_scores || {},
      }));
      
      setRealPlayerData(playerData);
    } catch (error) {
      console.error('Error fetching player data:', error);
      setPlayerDataError('Failed to load real player data');
      setRealPlayerData([]);
    } finally {
      setPlayerDataLoading(false);
    }
  }, [previewConfig.sortBy, previewConfig.sortOrder, previewConfig.playerCount]);

  // Fetch real player data when preview mode is enabled and config changes
  useEffect(() => {
    if (previewConfig.enabled && !previewConfig.mockData) {
      fetchRealPlayerData();
    }
  }, [previewConfig.enabled, previewConfig.mockData, previewConfig.sortBy, previewConfig.sortOrder, previewConfig.playerCount, fetchRealPlayerData]);

  // Get elements to display (with preview data if preview mode is enabled)
  const displayElements = useMemo(() => {
    if (!previewConfig.enabled) {
      return elements;
    }

    // Use real data if available and not using mock data
    const useRealData = !previewConfig.mockData && realPlayerData.length > 0;
    const dataSource = useRealData ? realPlayerData : generateMockPlayerData(previewConfig.playerCount || 10);
    
    const previewElements: CanvasElement[] = [];
    
    // Add non-series elements first
    elements.forEach(element => {
      if (!element.dataBinding?.seriesId) {
        previewElements.push(element);
      }
    });

    // Add elements from series with data
    elementSeries.forEach(series => {
      const seriesElements = generateElementsFromSeries(series, dataSource);
      previewElements.push(...seriesElements);
    });

    return previewElements;
  }, [elements, elementSeries, previewConfig, realPlayerData]);

  

  const deleteElement = useCallback(
    (elementId: string) => {
      const { updatedElements, removed } = removeCanvasElement(elements, elementId);
      if (!removed) return;

      setElements(updatedElements);
      setCanvasData((prevData) => ({
        ...prevData,
        elements: updatedElements,
      }));
      setSelectedElement((prev) => (prev?.id === elementId ? null : prev));

      addToHistory(HistoryManager.createActionTypes.deleteElement(removed));
    },
    [elements, addToHistory],
  );

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
        const canvasWidth = canvasSettings.width;
        const canvasHeight = canvasSettings.height;
        
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
  }, [canvasSettings, zoom, pan, addToHistory]);

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

    switch (action.type) {
      case 'add_element':
        setElements((prev) => {
          const next = prev.filter((el) => el.id !== action.data.elementId);
          setCanvasData((prevData) => ({ ...prevData, elements: next }));
          setSelectedElement((current) =>
            current?.id === action.data.elementId ? null : current,
          );
          return next;
        });
        break;
      case 'update_element':
        setElements((prev) => {
          const next = prev.map((el) =>
            el.id === action.data.elementId ? action.data.before : el,
          );
          setCanvasData((prevData) => ({ ...prevData, elements: next }));
          setSelectedElement((current) =>
            current?.id === action.data.elementId ? action.data.before : current,
          );
          return next;
        });
        break;
      case 'delete_element':
        setElements((prev) => {
          const next = [...prev, action.data.before];
          setCanvasData((prevData) => ({ ...prevData, elements: next }));
          return next;
        });
        break;
      case 'update_background':
        setBackgroundImage(action.data.before);
        setCanvasData((prevData) => ({ ...prevData, backgroundImage: action.data.before }));
        break;
      case 'update_settings':
        if (action.data.before.settings) {
          setCanvasData((prevData) =>
            updateCanvasSettings(prevData, action.data.before.settings),
          );
        }
        if (action.data.before.zoom !== undefined) setZoom(action.data.before.zoom);
        if (action.data.before.pan !== undefined) setPan(action.data.before.pan);
        if (action.data.before.gridVisible !== undefined)
          setGridVisible(action.data.before.gridVisible);
        if (action.data.before.gridSnapEnabled !== undefined)
          setGridSnapEnabled(action.data.before.gridSnapEnabled);
        break;
    }

    setCanUndo(historyManagerRef.current.canUndo());
    setCanRedo(historyManagerRef.current.canRedo());
  }, []);

  const handleRedo = useCallback(() => {
    const action = historyManagerRef.current.redo();
    if (!action) return;

    switch (action.type) {
      case 'add_element':
        setElements((prev) => {
          const next = [...prev, action.data.after];
          setCanvasData((prevData) => ({ ...prevData, elements: next }));
          return next;
        });
        break;
      case 'update_element':
        setElements((prev) => {
          const next = prev.map((el) =>
            el.id === action.data.elementId ? action.data.after : el,
          );
          setCanvasData((prevData) => ({ ...prevData, elements: next }));
          setSelectedElement((current) =>
            current?.id === action.data.elementId ? action.data.after : current,
          );
          return next;
        });
        break;
      case 'delete_element':
        setElements((prev) => {
          const next = prev.filter((el) => el.id !== action.data.elementId);
          setCanvasData((prevData) => ({ ...prevData, elements: next }));
          setSelectedElement((current) =>
            current?.id === action.data.elementId ? null : current,
          );
          return next;
        });
        break;
      case 'update_background':
        setBackgroundImage(action.data.after);
        setCanvasData((prevData) => ({ ...prevData, backgroundImage: action.data.after }));
        break;
      case 'update_settings':
        if (action.data.after.settings) {
          setCanvasData((prevData) =>
            updateCanvasSettings(prevData, action.data.after.settings),
          );
        }
        if (action.data.after.zoom !== undefined) setZoom(action.data.after.zoom);
        if (action.data.after.pan !== undefined) setPan(action.data.after.pan);
        if (action.data.after.gridVisible !== undefined)
          setGridVisible(action.data.after.gridVisible);
        if (action.data.after.gridSnapEnabled !== undefined)
          setGridSnapEnabled(action.data.after.gridSnapEnabled);
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
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      const target = e.target as HTMLElement;
      const elementElement = target.closest('[data-element-id]');

      if (elementElement) {
        const elementId = elementElement.getAttribute('data-element-id');
        if (elementId) {
          const element = elements.find((item) => item.id === elementId);
          if (element) {
            setDraggedElement(elementId);
            setDragStart({ x: e.clientX, y: e.clientY });
            setSelectedElement(element);
            e.preventDefault();
            e.stopPropagation();
            return;
          }
        }
      }

      if (e.button === 0 || e.button === 1 || e.button === 2) {
        setIsDragging(true);
        setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
        e.preventDefault();
      }
    },
    [elements, pan],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (draggedElement) {
        const element = elements.find((item) => item.id === draggedElement);
        if (element) {
          const deltaX = (e.clientX - dragStart.x) / zoom;
          const deltaY = (e.clientY - dragStart.y) / zoom;

          const snappedPosition = applyElementSnapping(element, {
            x: snapToGrid(element.x + deltaX),
            y: snapToGrid(element.y + deltaY),
          });

          const constrained = clampPositionToCanvas(snappedPosition, element, canvasSettings);

          const threshold = 1;
          if (
            Math.abs(constrained.x - element.x) >= threshold ||
            Math.abs(constrained.y - element.y) >= threshold
          ) {
            updateElement(draggedElement, {
              x: constrained.x,
              y: constrained.y,
            });
            setDragStart({ x: e.clientX, y: e.clientY });
          }
        }
      } else if (isDragging) {
        setPan({
          x: e.clientX - dragStart.x,
          y: e.clientY - dragStart.y,
        });
        setSnapLines([]);
      }
    },
    [
      applyElementSnapping,
      canvasSettings,
      dragStart.x,
      dragStart.y,
      draggedElement,
      elements,
      isDragging,
      snapToGrid,
      updateElement,
      zoom,
    ],
  );

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
  useEffect(() => {
    if (!lock) return;

    const interval = window.setInterval(async () => {
      try {
        const refreshedLock = await refreshLock(graphic.id);
        if (refreshedLock) {
          setLock(refreshedLock);
        }
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
  }, [lock, graphic.id, refreshLock, toast]);

  // Release lock on unmount
  useEffect(() => {
    return () => {
      if (lock && lock.user_name === username) {
        releaseLock(graphic.id).catch((error) => {
          console.error('Error releasing lock:', error);
          toast({
            title: 'Lock release failed',
            description: 'We could not release the editing lock cleanly.',
            variant: 'destructive',
          });
        });
      }
    };
  }, [lock, graphic.id, username, releaseLock, toast]);

  const handleSave = async () => {
    if (!title.trim() || !eventName.trim()) {
      toast({
        title: 'Missing details',
        description: 'Title and event name are required before saving.',
        variant: 'destructive',
      });
      return;
    }

    setSaving(true);
    try {
      const payload: CanvasState = {
        ...canvasData,
        elements,
        elementSeries,
        backgroundImage,
        previewConfig,
      };

      const success = await onSave({
        title: title.trim(),
        event_name: eventName.trim(),
        data_json: serializeCanvasState(payload),
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

  const handleReleaseLock = async () => {
    if (lock && lock.user_name === username) {
      try {
        await releaseLock(graphic.id);
        setLock(null);
      } catch (error) {
        console.error('Error releasing lock:', error);
        toast({
          title: 'Lock release failed',
          description: 'We were unable to release the lock for this graphic.',
          variant: 'destructive',
        });
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
      toast({
        title: 'Lock refresh failed',
        description: 'Unable to refresh the editing lock.',
        variant: 'destructive',
      });
    }
  }, [graphic.id, refreshLock, toast]);

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
    <div className="fixed inset-0 bg-background z-30 flex flex-col">
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
            size="sm"
            onClick={handleClose}
            disabled={saving}
          >
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={saving || !title.trim() || !eventName.trim()}
            className="flex items-center gap-1"
          >
            <Save className="h-4 w-4" />
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex flex-1 overflow-hidden">
          <div className={`${sidebarCollapsed ? 'w-12' : 'w-80'} border-r bg-muted flex flex-col transition-all duration-200 h-full`}>
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
            <Tabs value={activeTab} onValueChange={setActiveTab} className="flex h-full flex-col overflow-hidden">
              <div className="border-b bg-card px-2 flex-shrink-0">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="design" className="data-[state=active]:bg-blue-600 data-[state=active]:text-white">Design</TabsTrigger>
                  <TabsTrigger value="elements" className="data-[state=active]:bg-blue-600 data-[state=active]:text-white">Elements</TabsTrigger>
                </TabsList>
              </div>

              <div className="flex-1 overflow-hidden">
                <TabsContent value="design" className="m-0 h-full overflow-auto p-2">
                  <div className="p-4 space-y-4">
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Elements</CardTitle>
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
                          onClick={() => addPropertyElement('players')}
                        >
                          <User className="h-4 w-4 mr-2" />
                          Players Element
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full justify-start"
                          onClick={addScoresElementWithRound}
                        >
                          <Trophy className="h-4 w-4 mr-2" />
                          Scores Element ({selectedRound})
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full justify-start"
                          onClick={() => addPropertyElement('placement')}
                        >
                          <Medal className="h-4 w-4 mr-2" />
                          Placement Element
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

                            {(selectedElement.type === 'text' || ['players', 'scores', 'placement'].includes(selectedElement.type)) && (
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

                            {['players', 'scores', 'placement'].includes(selectedElement.type) && (
                              <>
                                <div>
                                  <label className="text-xs text-muted-foreground">Type</label>
                                  <div className="text-sm font-medium capitalize flex items-center gap-2">
                                    {selectedElement.type === 'players' && <User className="h-4 w-4" />}
                                    {selectedElement.type === 'scores' && <Trophy className="h-4 w-4" />}
                                    {selectedElement.type === 'placement' && <Medal className="h-4 w-4" />}
                                    {selectedElement.type} Property
                                  </div>
                                </div>

                                {selectedElement.type === 'scores' && (
                                  <div>
                                    <label className="text-xs text-muted-foreground">Round Selection</label>
                                    <Select
                                      value={selectedRound}
                                      onValueChange={setSelectedRound}
                                    >
                                      <SelectTrigger className="h-10">
                                        <SelectValue placeholder="Select round..." />
                                      </SelectTrigger>
                                      <SelectContent>
                                        <SelectItem value="round_1">Round 1</SelectItem>
                                        <SelectItem value="round_2">Round 2</SelectItem>
                                        <SelectItem value="round_3">Round 3</SelectItem>
                                        <SelectItem value="round_4">Round 4</SelectItem>
                                        <SelectItem value="round_5">Round 5</SelectItem>
                                        <SelectItem value="total_points">Total Points</SelectItem>
                                      </SelectContent>
                                    </Select>
                                  </div>
                                )}

                                <div>
                                  <label className="text-xs text-muted-foreground">Element Spacing (px)</label>
                                  <Input
                                    type="number"
                                    min={0}
                                    value={selectedElement.spacing ?? 20}
                                    onChange={(e) =>
                                      updateElement(selectedElement.id, { spacing: Number(e.target.value) || 20 })
                                    }
                                    placeholder="Space between items"
                                  />
                                </div>
                              </>
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

                <TabsContent value="elements" className="m-0 h-full overflow-auto p-2">
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

  


              </div>
            </Tabs>
          )}
        </div>

        <div className="flex-1 bg-muted overflow-hidden relative">
          <div
            ref={canvasRef}
            className="absolute inset-0 bg-card overflow-hidden z-10"
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

            {displayElements.map((element) => (
              <div
                key={element.id}
                data-element-id={element.id}
                className={`absolute cursor-move ${selectedElement?.id === element.id ? 'ring-2 ring-blue-500' : ''} ${previewConfig.enabled ? 'pointer-events-none' : ''}`}
                style={{
                  left: `${element.x * zoom}px`,
                  top: `${element.y * zoom}px`,
                  width: element.type === 'text' ? 'auto' : `${(element.width || 100) * zoom}px`,
                  height: element.type === 'text' ? 'auto' : `${(element.height || 50) * zoom}px`,
                  zIndex: 1
                }}
                onClick={(e) => {
                  if (!previewConfig.enabled) {
                    e.stopPropagation();
                    setSelectedElement(element);
                  }
                }}
              >
                {(element.type === 'text' || ['players', 'scores', 'placement'].includes(element.type)) && (
                  <div
                    style={{
                      ...elementStyleToCss(element),
                      fontSize: `${(element.fontSize || 16) * zoom}px`,
                      whiteSpace: 'nowrap',
                      padding: element.padding 
                        ? `${(element.padding.top || 4) * zoom}px ${(element.padding.right || 8) * zoom}px ${(element.padding.bottom || 4) * zoom}px ${(element.padding.left || 8) * zoom}px`
                        : `${4 * zoom}px ${8 * zoom}px`,
                      borderRadius: element.borderRadius ? `${element.borderRadius * zoom}px` : `${4 * zoom}px`,
                      borderWidth: element.borderWidth ? `${element.borderWidth * zoom}px` : '1px',
                      letterSpacing: element.letterSpacing ? `${element.letterSpacing * zoom}px` : undefined,
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

      <div className="border-t bg-card p-4 relative z-20">
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

            {/* Center - Preview toggle */}
            <div className="flex items-center gap-2">
              <Button
                variant={previewConfig.enabled ? "default" : "outline"}
                size="sm"
                onClick={togglePreviewMode}
                className="flex items-center gap-1"
              >
                <Settings className="h-4 w-4" />
                {previewConfig.enabled ? 'Preview ON' : 'Preview OFF'}
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
