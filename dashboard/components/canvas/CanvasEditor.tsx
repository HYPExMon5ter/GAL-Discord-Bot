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
  ElementType,
  SnapLine,
  CanvasDataBinding,
  ElementDataBinding,
  CanvasBindingSource,
  CanvasBindingField,
  ElementSeries,
  ElementSpacing,
  PlayerData,
  PreviewModeConfig,
  UniversalStyleControls,
  StylePreset,
  ELEMENT_CONFIGS,
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
  Users,
  Trophy,
  Medal,
  Target,
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
  updatePreviewModeConfig,
  getElementsWithPreviewData,
  createSimplifiedBinding,
  createAutoPopulatedPlayersSeries,
  createRoundScoreElement,
  createSmartScoreElement,
  createSmartPlacementElement,
} from '@/lib/canvas-helpers';
import {
  elementStyleToCss,
  getDefaultPreviewModeConfig,
  generateMockPlayerData,
} from '@/lib/canvas-styling';

// Helper to get simplified binding for any element
function getSimplifiedBinding(element: CanvasElement): ElementDataBinding {
  const existing = element.dataBinding;
  
  // Check if it's already in the new format
  if (existing && (existing.source === 'static' || existing.source === 'dynamic')) {
    return existing as ElementDataBinding;
  }
  
  // Convert legacy binding or create new one
  return createSimplifiedBinding(element);
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
  const [activeTab, setActiveTab] = useState('design');
  const canvasSettings = canvasData?.settings ?? DEFAULT_CANVAS_SETTINGS;
  
  // Styling system state
  const [previewConfig, setPreviewConfig] = useState<PreviewModeConfig>(
    initialCanvasState.previewConfig || getDefaultPreviewModeConfig()
  );
  
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
  
  // Round options for Scores elements
  const [roundOptions] = useState([
    { value: 'round_1', label: 'Round 1' },
    { value: 'round_2', label: 'Round 2' },
    { value: 'round_3', label: 'Round 3' },
    { value: 'round_4', label: 'Round 4' },
    { value: 'round_5', label: 'Round 5' },
    { value: 'round_6', label: 'Round 6' },
  ]);
  
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
  
  // Enhanced dynamic elements state
  const [elementSpacing, setElementSpacing] = useState(56);
  const [selectedSortBy, setSelectedSortBy] = useState<'total_points' | 'player_name' | 'standing_rank'>('total_points');
  const [selectedSortOrder, setSelectedSortOrder] = useState<'asc' | 'desc'>('desc');
  
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
  const snapshotInputRef = useRef<HTMLInputElement>(null);

  // Simplified element binding update function
  function updateElementBinding(elementId: string, updates: Partial<ElementDataBinding>) {
    const element = elements.find(item => item.id === elementId);
    if (!element) return;

    const currentBinding = getSimplifiedBinding(element);
    const newBinding: ElementDataBinding = {      ...currentBinding,
      ...updates,
    };

    updateElement(elementId, { 
      dataBinding: newBinding,
    });
  }

  // Simplified dynamic elements tracking
  const dynamicElements = useMemo(() => {
    return elements.filter(element => 
      ['player_name', 'player_score', 'player_placement', 'team_name', 'round_score'].includes(element.type)
    );
  }, [elements]);

  

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

  const addPropertyElement = useCallback((propertyType: CanvasPropertyType) => {
    const newElement = createPropertyElement(propertyType, snapToGrid);
    
    // Create element series for auto-generation
    const newSeries = createElementSeries(
      propertyType,
      newElement,
      { horizontal: 0, vertical: 56, direction: 'vertical' }  // Default vertical spacing
    );
    
    // Apply simplified dynamic binding with series reference
    const simplifiedBinding = createSimplifiedBinding(newElement);
    const elementWithBinding = { 
      ...newElement, 
      dataBinding: {
        ...simplifiedBinding,
        seriesId: newSeries.id,
      }
    };
    
    // Add series first
    setElementSeries((previous) => {
      const nextSeries = [...previous, newSeries];
      setCanvasData((prevData) => ({
        ...prevData,
        elementSeries: nextSeries,
      }));
      return nextSeries;
    });
    
    // Add element
    setElements((previous) => {
      const nextElements = [...previous, elementWithBinding];
      setCanvasData((prevData) => ({
        ...prevData,
        elements: nextElements,
      }));
      return nextElements;
    });
    
    setSelectedElement(elementWithBinding);

    // Automatically fetch real player data for all dynamic elements
    fetchRealPlayerData();

    addToHistory(HistoryManager.createActionTypes.addElement(elementWithBinding));
  }, [snapToGrid, addToHistory, fetchRealPlayerData]);

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

  // Enhanced dynamic element creation with auto-population and sorting
  const addAutoPopulatedPlayers = useCallback((sortBy: 'total_points' | 'player_name' | 'standing_rank' = 'total_points', sortOrder: 'asc' | 'desc' = 'desc') => {
    // This will create a series that auto-populates with all tournament players
    const baseElement = createPropertyElement('player_name', snapToGrid);
    
    const enhancedSeries: ElementSeries = {
      id: `auto-players-${Date.now()}`,
      type: 'player_name',
      baseElement,
      spacing: { horizontal: 0, vertical: 56, direction: 'vertical' }, // Default vertical spacing
      autoGenerate: true,
      maxElements: 50, // Reasonable limit
      sortBy,
      sortOrder,
    };
    
    // Link element to series
    const elementWithBinding = {
      ...baseElement,
      dataBinding: {
        ...createSimplifiedBinding(baseElement),
        seriesId: enhancedSeries.id,
      }
    };
    
    // Add series
    setElementSeries((previous) => {
      const nextSeries = [...previous, enhancedSeries];
      setCanvasData((prevData) => ({
        ...prevData,
        elementSeries: nextSeries,
      }));
      return nextSeries;
    });
    
    // CRITICAL FIX: Add base element to elements array (this was missing!)
    setElements((previous) => {
      const nextElements = [...previous, elementWithBinding];
      setCanvasData((prevData) => ({
        ...prevData,
        elements: nextElements,
      }));
      return nextElements;
    });
    
    setSelectedElement(elementWithBinding);
    addToHistory(HistoryManager.createActionTypes.addElement(elementWithBinding));
    
    // Automatically fetch real player data to ensure auto-population has latest data
    fetchRealPlayerData();
    
    toast({
      title: 'Auto-populated Players Added',
      description: `Added players series sorted by ${sortBy} (${sortOrder})`,
    });
  }, [snapToGrid, addToHistory, toast, fetchRealPlayerData]);

  // Add round-specific score elements
  const addRoundScores = useCallback((roundId: string) => {
    const baseElement = createRoundScoreElement(snapToGrid, roundId);
    
    // Create a series for round scores to enable auto-population
    const roundSeries: ElementSeries = {
      id: `round-scores-${roundId}-${Date.now()}`,
      type: 'round_score',
      baseElement,
      spacing: { horizontal: 0, vertical: 56, direction: 'vertical' },
      autoGenerate: true,
      maxElements: 50,
      sortBy: 'total_points',
      sortOrder: 'desc',
      roundId, // Store roundId in the series
    };
    
    // Link element to series
    const elementWithBinding: CanvasElement = {
      ...baseElement,
      dataBinding: {
        ...baseElement.dataBinding,
        seriesId: roundSeries.id,
      } as ElementDataBinding
    };
    
    // Add series first
    setElementSeries((previous) => {
      const nextSeries = [...previous, roundSeries];
      setCanvasData((prevData) => ({
        ...prevData,
        elementSeries: nextSeries,
      }));
      return nextSeries;
    });
    
    // Add element
    setElements((previous) => {
      const nextElements = [...previous, elementWithBinding];
      setCanvasData((prevData) => ({
        ...prevData,
        elements: nextElements,
      }));
      return nextElements;
    });
    
    setSelectedElement(elementWithBinding);
    addToHistory(HistoryManager.createActionTypes.addElement(elementWithBinding));
    
    // Automatically fetch real player data to ensure round scores have latest data
    fetchRealPlayerData();
    
    toast({
      title: 'Round Scores Added',
      description: `Added scores series for ${roundId.replace('round_', 'Round ')}`,
    });
  }, [snapToGrid, addToHistory, toast, fetchRealPlayerData]);

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

      // If element is linked to series and position changed, update series baseElement
      const element = elements.find(e => e.id === elementId);
      if (element?.dataBinding?.seriesId && (updates.x !== undefined || updates.y !== undefined)) {
        const seriesId = element.dataBinding.seriesId;
        const currentSeries = elementSeries.find(s => s.id === seriesId);
        if (currentSeries) {
          console.log('Updating series baseElement position:', {
            seriesId,
            oldPosition: { x: currentSeries.baseElement.x, y: currentSeries.baseElement.y },
            newPosition: { 
              x: updates.x !== undefined ? updates.x : element.x, 
              y: updates.y !== undefined ? updates.y : element.y 
            }
          });
          setElementSeries(prev => 
            updateElementSeries(prev, seriesId, {
              baseElement: {
                ...currentSeries.baseElement,
                x: updates.x !== undefined ? updates.x : element.x,
                y: updates.y !== undefined ? updates.y : element.y,
              }
            })
          );
        }
      }

      addToHistory(
        HistoryManager.createActionTypes.updateElement(
          elementId,
          result.previous,
          result.next,
        ),
      );
    },
    [elements, elementSeries, gridSize, gridSnapEnabled, addToHistory],
  );



  

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

  

  // Sync elementSpacing state when selection changes
  useEffect(() => {
    if (selectedElement?.dataBinding?.seriesId) {
      const seriesId = selectedElement.dataBinding.seriesId;
      const series = elementSeries.find(s => s.id === seriesId);
      if (series) {
        setElementSpacing(series.spacing.vertical);
      }
    }
  }, [selectedElement, elementSeries]);

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

    // Add elements from series with data, using the updated baseElement position
    elementSeries.forEach(series => {
      // Find the current base element position from the elements array
      const currentBaseElement = elements.find(el => el.id === series.baseElement.id);
      const updatedSeries = {
        ...series,
        baseElement: currentBaseElement || series.baseElement
      };
      
      console.log('Preview mode generating elements for series:', {
        seriesId: series.id,
        seriesType: series.type,
        baseElementId: series.baseElement.id,
        originalPosition: { x: series.baseElement.x, y: series.baseElement.y },
        currentPosition: currentBaseElement ? { x: currentBaseElement.x, y: currentBaseElement.y } : null,
        roundId: series.roundId
      });
      
      const seriesElements = generateElementsFromSeries(updatedSeries, dataSource);
      previewElements.push(...seriesElements);
    });

    return previewElements;
  }, [elements, elementSeries, previewConfig, realPlayerData]);

  // Helper function to get display content for elements
  const getElementDisplayContent = (element: CanvasElement): string => {
    // Static text elements
    if (element.type === 'text') {
      return element.content || 'Text';
    }
    
    // Dynamic elements without data binding
    if (!element.dataBinding || element.dataBinding.source !== 'dynamic') {
      return element.placeholderText || ELEMENT_CONFIGS[element.type]?.label || 'Data';
    }
    
    // Handle both ElementDataBinding and CanvasDataBinding
    const binding = element.dataBinding;
    
    // Series-generated elements have manualValue pre-populated (CanvasDataBinding)
    if ('manualValue' in binding && binding.seriesId && binding.manualValue) {
      return binding.manualValue;
    }
    
    // Fallback to placeholder
    return ('fallbackText' in binding && binding.fallbackText) || element.placeholderText || 'Loading...';
  };

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

  // Main render logic

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

      <div className="flex-1 flex overflow-hidden">
        <div className={`${sidebarCollapsed ? 'w-12' : 'w-64'} border-r bg-muted flex flex-col transition-all duration-200 h-full`}>
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

          {/* Tabs Section - Takes remaining space */}
          {!sidebarCollapsed && (
            <div className="flex-1 flex flex-col overflow-hidden">
                <Tabs value={activeTab} onValueChange={setActiveTab} className="flex h-full flex-col overflow-hidden">
              <div className="border-b bg-card px-2 flex-shrink-0">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="design" className="data-[state=active]:bg-blue-600 data-[state=active]:text-white">Properties</TabsTrigger>
                  <TabsTrigger value="elements" className="data-[state=active]:bg-blue-600 data-[state=active]:text-white">Layers</TabsTrigger>
                </TabsList>
              </div>

              <div className="flex-1 overflow-hidden">
                <TabsContent value="design" className="m-0 h-full overflow-auto p-2">
                  <div className="p-4 space-y-4">
                    {/* Canvas Tools Section - positioned at the top */}
                    <div className="space-y-4">
                      <div className="p-2">
                        <div className="space-y-2">
                          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider text-center">
                            Canvas Tools
                          </h3>
                          
                          {/* Background Upload Button */}
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full justify-start text-left h-auto py-2 px-4 min-w-[200px]"
                            onClick={() => fileInputRef.current?.click()}
                          >
                            <Upload className="h-4 w-4 mr-2 flex-shrink-0" />
                            <span className="text-sm">Background Upload</span>
                          </Button>
                          <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*"
                            onChange={handleBackgroundUpload}
                            className="hidden"
                          />
                          
                          {/* Core Elements - with consistent spacing */}
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full justify-start text-left h-auto py-2 px-4 min-w-[200px]"
                            onClick={() => addTextElement()}
                          >
                            <Type className="h-4 w-4 mr-2 flex-shrink-0" />
                            <span className="text-sm">Add Text</span>
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full justify-start text-left h-auto py-2 px-4 min-w-[200px]"
                            onClick={() => addAutoPopulatedPlayers('total_points', 'desc')}
                          >
                            <Users className="h-4 w-4 mr-2 flex-shrink-0" />
                            <span className="text-sm">Players</span>
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full justify-start text-left h-auto py-2 px-4 min-w-[200px]"
                            onClick={() => addPropertyElement('player_score')}
                          >
                            <Trophy className="h-4 w-4 mr-2 flex-shrink-0" />
                            <span className="text-sm">Scores</span>
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full justify-start text-left h-auto py-2 px-4 min-w-[200px]"
                            onClick={() => addPropertyElement('player_placement')}
                          >
                            <Medal className="h-4 w-4 mr-2 flex-shrink-0" />
                            <span className="text-sm">Placements</span>
                          </Button>
                        </div>
                      </div>
                    </div>

                    {/* Full Visual Separator between Canvas Tools and Element Properties */}
                    <div className="border-t-2 border-gray-400 dark:border-gray-500 -mx-8 my-8 opacity-80"></div>
                    
                    {/* Element Properties Section - Show below Canvas Tools and divider */}
                    {selectedElement && (
                      <div className="space-y-4">
                        <div className="p-2">
                          <div className="space-y-2">
                            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider text-center">
                              Element Properties
                            </h3>
                          </div>
                        </div>
                        <div className="space-y-3">
                          {/* Content (only for static text elements) */}
                          {selectedElement.type === 'text' && (
                            <div>
                              <label className="text-xs text-muted-foreground">Content</label>
                              <Input
                                value={selectedElement.content ?? ''}
                                onChange={(e) =>
                                  updateElement(selectedElement.id, { content: e.target.value })
                                }
                                placeholder="Enter text content..."
                                className="h-8"
                              />
                            </div>
                          )}

                          {/* Font Properties */}
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <label className="text-xs text-muted-foreground">Font Family</label>
                              <Select
                                value={selectedElement.fontFamily || 'Arial'}
                                onValueChange={(value) =>
                                  updateElement(selectedElement.id, { fontFamily: value })
                                }
                              >
                                <SelectTrigger className="h-8">
                                  <SelectValue />
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
                                className="h-8"
                              />
                            </div>
                          </div>

                          {/* Text Color */}
                          <div>
                            <label className="text-xs text-muted-foreground">Text Color</label>
                            <Input
                              type="color"
                              value={selectedElement.color ?? '#000000'}
                              onChange={(e) =>
                                updateElement(selectedElement.id, { color: e.target.value })
                              }
                              className="h-8 w-full"
                            />
                          </div>

                          {/* Round Selector - Only for Scores elements */}
                          {(selectedElement.type === 'player_score' || selectedElement.type === 'round_score') && (
                            <div>
                              <label className="text-xs text-muted-foreground">Round Selection</label>
                              <Select
                                value={selectedElement.dataBinding?.roundId || ''}
                                onValueChange={(value) => {
                                  console.log('Round selection changed:', value, 'for element:', selectedElement.id, 'type:', selectedElement.type);
                                  
                                  // Update both the element and its series if it exists
                                  if (selectedElement.dataBinding) {
                                    const updatedBinding = {
                                      ...selectedElement.dataBinding,
                                      roundId: value || undefined,
                                    };
                                    
                                    // Update the element
                                    updateElement(selectedElement.id, {
                                      dataBinding: updatedBinding
                                    });
                                    
                                    // If this element is part of a series, update the series as well
                                    if (selectedElement.dataBinding.seriesId) {
                                      const seriesId = selectedElement.dataBinding.seriesId;
                                      console.log('Updating series:', seriesId, 'with roundId:', value);
                                      setElementSeries(prev => 
                                        prev.map(series => 
                                          series.id === seriesId 
                                            ? { ...series, roundId: value || undefined }
                                            : series
                                        )
                                      );
                                    }
                                  }
                                }}
                              >
                                <SelectTrigger className="h-8">
                                  <SelectValue placeholder="Select round..." />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="">Total Score</SelectItem>
                                  {roundOptions.map((round) => (
                                    <SelectItem key={round.value} value={round.value}>
                                      {round.label}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                          )}

                          {/* Spacing Control - Only for series elements */}
                          {selectedElement.dataBinding?.seriesId && (
                            <div>
                              <label className="text-xs text-muted-foreground">Element Spacing (px)</label>
                              <Input
                                type="number"
                                min={0}
                                value={elementSpacing}
                                onChange={(e) => {
                                  const newSpacing = Number(e.target.value) || 0;
                                  setElementSpacing(newSpacing);
                                  
                                  // Update the series spacing
                                  const seriesId = selectedElement.dataBinding?.seriesId;
                                  if (seriesId) {
                                    setElementSeries(prev => 
                                      updateElementSeries(prev, seriesId, {
                                        spacing: { horizontal: 0, vertical: newSpacing, direction: 'vertical' }
                                      })
                                    );
                                  }
                                }}
                                className="h-8"
                              />
                            </div>
                          )}

                          {/* Element Type Info */}
                          <div className="text-xs text-muted-foreground p-2 bg-muted rounded">
                            <div>Type: {selectedElement.type}</div>
                            <div>ID: {selectedElement.id.slice(0, 8)}...</div>
                            {selectedElement.dataBinding?.source === 'dynamic' && (
                              <div className="text-green-600">Uses tournament data</div>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
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
            </div>
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
                {(element.type === 'text' || ['player_name', 'player_score', 'player_placement', 'team_name', 'round_score'].includes(element.type)) && (
                  <div
                    style={{
                      ...elementStyleToCss(element),
                      fontSize: `${(element.fontSize || 16) * zoom}px`,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {getElementDisplayContent(element)}
                  </div>
                )}
              </div>
            ))}
            </div>
          </div>
        </div>
      </div>

      <div className="border-t bg-card p-3 relative z-20">
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
            </div>

            {/* Center - Enhanced Preview controls */}
            <div className="flex items-center gap-2">
              <Button
                variant={previewConfig.enabled ? "default" : "outline"}
                size="sm"
                onClick={togglePreviewMode}
                className="min-w-[140px]"
              >
                <Settings className="h-4 w-4 mr-2" />
                {previewConfig.enabled ? 'Preview ON' : 'Preview OFF'}
              </Button>
              
              {previewConfig.enabled && (
                <div className="flex items-center gap-2 border-l pl-2">
                  <span className="text-xs text-muted-foreground">
                    {realPlayerData.length > 0 
                      ? `${realPlayerData.length} players` 
                      : playerDataLoading 
                      ? 'Loading...' 
                      : playerDataError 
                      ? 'Error' 
                      : 'No data'}
                  </span>
                  {!previewConfig.mockData && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={fetchRealPlayerData}
                      disabled={playerDataLoading}
                      className="h-7 text-xs"
                    >
                      <RefreshCw className={`h-3 w-3 mr-1 ${playerDataLoading ? 'animate-spin' : ''}`} />
                      Refresh
                    </Button>
                  )}
                </div>
              )}
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
  );
}
