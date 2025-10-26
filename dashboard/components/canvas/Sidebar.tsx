'use client';

import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ToolsTab } from './ToolsTab';
import { LayersTab } from './LayersTab';
import { PropertiesPanel } from './PropertiesPanel';
import type { CanvasElement } from '@/lib/canvas/types';

interface SidebarProps {
  elements: CanvasElement[];
  selectedElementId: string | null;
  onSelectElement: (elementId: string) => void;
  onDeleteElement: (elementId: string) => void;
  onUpdateElement: (elementId: string, updates: Partial<CanvasElement>) => void;
  onAddElement: (type: 'text' | 'players' | 'scores' | 'placements') => void;
  onBackgroundUpload: (file: File) => void;
  disabled?: boolean;
}

export function Sidebar({
  elements,
  selectedElementId,
  onSelectElement,
  onDeleteElement,
  onUpdateElement,
  onAddElement,
  onBackgroundUpload,
  disabled = false
}: SidebarProps) {
  const [activeTab, setActiveTab] = useState<'tools' | 'layers'>('tools');

  const selectedElement = elements.find(el => el.id === selectedElementId);

  const handleElementChange = (updates: Partial<CanvasElement>) => {
    if (selectedElementId) {
      onUpdateElement(selectedElementId, updates);
    }
  };

  return (
    <div className="w-64 border-r bg-muted flex flex-col">
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'tools' | 'layers')}>
        <div className="border-b bg-card p-2">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="tools">Tools</TabsTrigger>
            <TabsTrigger value="layers">Layers</TabsTrigger>
          </TabsList>
        </div>

        <div className="flex-1 flex flex-col">
          <TabsContent value="tools" className="flex-1 m-0">
            <ToolsTab
              onAddElement={onAddElement}
              onBackgroundUpload={onBackgroundUpload}
              disabled={disabled}
            />
          </TabsContent>

          <TabsContent value="layers" className="flex-1 m-0">
            <LayersTab
              elements={elements}
              selectedElementId={selectedElementId}
              onSelectElement={onSelectElement}
              onDeleteElement={onDeleteElement}
              disabled={disabled}
            />
          </TabsContent>
        </div>
      </Tabs>

      {/* Properties Panel - Fixed at bottom */}
      <div className="border-t bg-card">
        <PropertiesPanel
          element={selectedElement || null}
          onChange={handleElementChange}
          disabled={disabled}
        />
      </div>
    </div>
  );
}
