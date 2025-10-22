/**
 * SimplifiedPropertiesPanel Component
 * 
 * A redesigned properties panel that provides better organization
 * and separates concerns clearly for easier editing.
 */

'use client';

import { useState } from 'react';
import {
  CanvasElement,
  ElementType,
  ElementDataBinding,
  CanvasBindingField,
} from '@/types';
import { ELEMENT_CONFIGS } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ChevronDown, ChevronUp, Type, User, Trophy, Medal, Users, Target } from 'lucide-react';

interface SimplifiedPropertiesPanelProps {
  selectedElement: CanvasElement | null;
  onUpdateElement: (elementId: string, updates: Partial<CanvasElement>) => void;
  onUpdateBinding: (elementId: string, updates: Partial<ElementDataBinding>) => void;
  fontOptions: Array<{ value: string; label: string }>;
}

// Helper to check if element uses new binding system
function isElementDataBinding(binding: any): binding is ElementDataBinding {
  return binding && (binding.source === 'static' || binding.source === 'dynamic');
}

// Helper to convert legacy binding to new format
function convertToNewBinding(element: CanvasElement): ElementDataBinding | null {
  const legacyBinding = element.dataBinding;
  if (!legacyBinding) return null;
  
  if (isElementDataBinding(legacyBinding)) {
    return legacyBinding;
  }

  // Convert legacy binding
  const isManual = legacyBinding.source === 'manual';
  const elementConfig = ELEMENT_CONFIGS[element.dataType || element.type];
  
  return {
    source: isManual ? 'static' : 'dynamic',
    dataType: element.dataType || element.type as ElementType,
    staticValue: isManual ? (legacyBinding.manualValue || element.content) : undefined,
    snapshotId: legacyBinding.dataset?.snapshotId || 'latest',
    roundId: legacyBinding.dataset?.roundId,
    fallbackText: legacyBinding.fallbackText || elementConfig?.label,
  };
}

export function SimplifiedPropertiesPanel({
  selectedElement,
  onUpdateElement,
  onUpdateBinding,
  fontOptions,
}: SimplifiedPropertiesPanelProps) {
  const [expandedSections, setExpandedSections] = useState({
    basic: true,
    styling: true,
    data: true,
    advanced: false,
  });

  if (!selectedElement) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">
            Select an element to edit properties
          </p>
        </CardContent>
      </Card>
    );
  }

  const elementConfig = ELEMENT_CONFIGS[selectedElement.type];
  const isDynamic = elementConfig.category === 'dynamic';
  const binding = convertToNewBinding(selectedElement);

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section as keyof typeof prev]
    }));
  };

  const getElementIcon = (type: ElementType) => {
    switch (type) {
      case 'text': return <Type className="h-4 w-4" />;
      case 'player_name': return <User className="h-4 w-4" />;
      case 'player_score': return <Trophy className="h-4 w-4" />;
      case 'player_placement': return <Medal className="h-4 w-4" />;
      case 'team_name': return <Users className="h-4 w-4" />;
      case 'round_score': return <Target className="h-4 w-4" />;
      default: return <Type className="h-4 w-4" />;
    }
  };

  return (
    <div className="space-y-4">
      {/* Element Overview */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            {getElementIcon(selectedElement.type)}
            <span>{elementConfig.label}</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <p className="text-xs text-muted-foreground">
            {elementConfig.description}
          </p>
          <div className="mt-2 flex items-center gap-2">
            <span className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded">
              {elementConfig.category}
            </span>
            <span className="text-xs px-2 py-1 bg-gray-100 text-gray-800 rounded">
              {selectedElement.type}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Basic Properties */}
      <Card>
        <Collapsible
          open={expandedSections.basic}
          onOpenChange={() => toggleSection('basic')}
        >
          <CollapsibleTrigger className="w-full px-4 py-3 hover:bg-muted/50">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Basic Properties</span>
              {expandedSections.basic ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </div>
          </CollapsibleTrigger>
          <CollapsibleContent className="px-4 pb-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="element-x">X Position</Label>
                <Input
                  id="element-x"
                  type="number"
                  value={selectedElement.x ?? 0}
                  onChange={(e) =>
                    onUpdateElement(selectedElement.id, { x: Number(e.target.value) || 0 })
                  }
                />
              </div>
              <div>
                <Label htmlFor="element-y">Y Position</Label>
                <Input
                  id="element-y"
                  type="number"
                  value={selectedElement.y ?? 0}
                  onChange={(e) =>
                    onUpdateElement(selectedElement.id, { y: Number(e.target.value) || 0 })
                  }
                />
              </div>
              <div>
                <Label htmlFor="element-width">Width</Label>
                <Input
                  id="element-width"
                  type="number"
                  min={0}
                  value={selectedElement.width ?? ''}
                  onChange={(e) =>
                    onUpdateElement(selectedElement.id, { width: Number(e.target.value) || undefined })
                  }
                  placeholder={isDynamic ? 'Auto' : undefined}
                />
              </div>
              <div>
                <Label htmlFor="element-height">Height</Label>
                <Input
                  id="element-height"
                  type="number"
                  min={0}
                  value={selectedElement.height ?? ''}
                  onChange={(e) =>
                    onUpdateElement(selectedElement.id, { height: Number(e.target.value) || undefined })
                  }
                  placeholder={isDynamic ? 'Auto' : undefined}
                />
              </div>
            </div>

            {/* Content for static elements */}
            {!isDynamic && (
              <div>
                <Label htmlFor="element-content">Content</Label>
                <Input
                  id="element-content"
                  value={selectedElement.content ?? ''}
                  onChange={(e) =>
                    onUpdateElement(selectedElement.id, { content: e.target.value })
                  }
                  placeholder="Enter text content..."
                />
              </div>
            )}
          </div>
        </Collapsible>
      </Card>

      {/* Data Binding - Only for dynamic elements */}
      {isDynamic && binding && (
        <Card>
          <Collapsible
            open={expandedSections.data}
            onOpenChange={() => toggleSection('data')}
          >
            <CollapsibleTrigger className="w-full px-4 py-3 hover:bg-muted/50">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Data Connection</span>
                {expandedSections.data ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </div>
            </CollapsibleTrigger>
            <CollapsibleContent className="px-4 pb-4 space-y-3">
              <div>
                <Label htmlFor="data-source">Data Source</Label>
                <Select
                  value={binding.source}
                  onValueChange={(value) =>
                    onUpdateBinding(selectedElement.id, {
                      source: value as 'static' | 'dynamic'
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="static">Static Value</SelectItem>
                    <SelectItem value="dynamic">Tournament Data</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {binding.source === 'static' ? (
                <div>
                  <Label htmlFor="static-value">Static Text</Label>
                  <Input
                    id="static-value"
                    value={binding.staticValue ?? ''}
                    onChange={(e) =>
                      onUpdateBinding(selectedElement.id, {
                        staticValue: e.target.value
                      })
                    }
                    placeholder="Enter static text..."
                  />
                </div>
              ) : (
                <>
                  <div>
                    <Label htmlFor="data-type">Data Type</Label>
                    <Select
                      value={binding.dataType || selectedElement.type}
                      onValueChange={(value) =>
                        onUpdateBinding(selectedElement.id, {
                          dataType: value as ElementType
                        })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="player_name">Player Name</SelectItem>
                        <SelectItem value="player_score">Total Points</SelectItem>
                        <SelectItem value="player_placement">Placement/Rank</SelectItem>
                        <SelectItem value="team_name">Team Name</SelectItem>
                        <SelectItem value="round_score">Round Score</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label htmlFor="snapshot-id">Snapshot</Label>
                    <Input
                      id="snapshot-id"
                      value={binding.snapshotId?.toString() || ''}
                      onChange={(e) =>
                        onUpdateBinding(selectedElement.id, {
                          snapshotId: e.target.value || 'latest'
                        })
                    }
                    placeholder="latest"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Use 'latest' for current data or enter a specific snapshot ID
                    </p>
                  </div>

                  {(binding.dataType === 'round_score' || binding.dataType === 'player_score') && (
                    <div>
                      <Label htmlFor="round-id">Round ID</Label>
                      <Input
                        id="round-id"
                        value={binding.roundId ?? ''}
                        onChange={(e) =>
                          onUpdateBinding(selectedElement.id, {
                            roundId: e.target.value.trim() || undefined
                          })
                        }
                        placeholder="round_1"
                      />
                    </div>
                  )}

                  <div>
                    <Label htmlFor="fallback-text">Fallback Text</Label>
                    <Input
                      id="fallback-text"
                      value={binding.fallbackText ?? ''}
                      onChange={(e) =>
                        onUpdateBinding(selectedElement.id, {
                          fallbackText: e.target.value
                        })
                      }
                      placeholder="Shown when data is unavailable..."
                    />
                  </div>
                </>
              )}
            </div>
          </Collapsible>
        </Card>
      )}

      {/* Styling Properties */}
      <Card>
        <Collapsible
          open={expandedSections.styling}
          onOpenChange={() => toggleSection('styling')}
        >
          <CollapsibleTrigger className="w-full px-4 py-3 hover:bg-muted/50">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Appearance</span>
              {expandedSections.styling ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </div>
          </CollapsibleTrigger>
          <CollapsibleContent className="px-4 pb-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="font-family">Font Family</Label>
                <Select
                  value={selectedElement.fontFamily || 'Arial'}
                  onValueChange={(value) =>
                    onUpdateElement(selectedElement.id, { fontFamily: value })
                  }
                >
                  <SelectTrigger>
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
                <Label htmlFor="font-size">Font Size</Label>
                <Input
                  id="font-size"
                  type="number"
                  min={8}
                  value={selectedElement.fontSize ?? 16}
                  onChange={(e) =>
                    onUpdateElement(selectedElement.id, { fontSize: Number(e.target.value) || 0 })
                  }
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="text-color">Text Color</Label>
                <Input
                  id="text-color"
                  type="color"
                  value={selectedElement.color ?? '#000000'}
                  onChange={(e) =>
                    onUpdateElement(selectedElement.id, { color: e.target.value })
                  }
                />
              </div>
              <div>
                <Label htmlFor="bg-color">Background Color</Label>
                <Input
                  id="bg-color"
                  type="color"
                  value={selectedElement.backgroundColor ?? '#3B82F6'}
                  onChange={(e) =>
                    onUpdateElement(selectedElement.id, { backgroundColor: e.target.value })
                  }
                />
              </div>
            </div>
          </div>
        </Collapsible>
      </Card>

      {/* Advanced Properties */}
      <Card>
        <Collapsible
          open={expandedSections.advanced}
          onOpenChange={() => toggleSection('advanced')}
        >
          <CollapsibleTrigger className="w-full px-4 py-3 hover:bg-muted/50">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Advanced</span>
              {expandedSections.advanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </div>
          </CollapsibleTrigger>
          <CollapsibleContent className="px-4 pb-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="element-id">Element ID</Label>
                <Input
                  id="element-id"
                  value={selectedElement.id}
                  disabled
                  className="text-muted-foreground"
                />
              </div>
              <div>
                <Label htmlFor="element-type">Type</Label>
                <Input
                  id="element-type"
                  value={selectedElement.type}
                  disabled
                  className="text-muted-foreground"
                />
              </div>
            </div>

            {/* Additional advanced properties can be added here */}
            <div>
              <Label htmlFor="data-binding-info">Binding Info</Label>
              <div className="p-2 bg-muted rounded text-xs">
                {JSON.stringify(binding, null, 2)}
              </div>
            </div>
          </div>
        </Collapsible>
      </Card>
    </div>
  );
}
