'use client';

import { memo, useEffect, useMemo, useRef, useState } from 'react';
import { Graphic, ArchivedGraphic } from '@/types';
import { Button } from '@/components/ui/button';
import {
  ChevronUp,
  ChevronDown,
  Edit,
  Copy,
  Archive as ArchiveIcon,
  Trash2,
  Eye,
  RotateCcw,
} from 'lucide-react';

interface GraphicsTableProps {
  graphics: (Graphic | ArchivedGraphic)[];
  loading: boolean;
  onEdit: (graphic: Graphic | ArchivedGraphic) => void;
  onDuplicate: (graphic: Graphic | ArchivedGraphic) => void;
  onArchive: (graphic: Graphic | ArchivedGraphic) => void;
  onDelete: (graphic: Graphic | ArchivedGraphic) => void;
  onView: (graphic: Graphic | ArchivedGraphic) => void;
  onUnarchive?: (graphic: Graphic | ArchivedGraphic) => void;
  onRestore?: (graphic: Graphic | ArchivedGraphic) => void;
  isArchived?: boolean;
  selectable?: boolean;
  selectedIds?: number[];
  onToggleSelect?: (graphicId: number) => void;
  onToggleSelectAll?: (selecting: boolean) => void;
}

type SortField = 'title' | 'event_name' | 'updated_at' | 'archived_at';
type SortDirection = 'asc' | 'desc';

const GraphicsTableComponent = ({
  graphics,
  loading,
  onEdit,
  onDuplicate,
  onArchive,
  onDelete,
  onView,
  onUnarchive,
  onRestore,
  isArchived = false,
  selectable = false,
  selectedIds = [],
  onToggleSelect,
  onToggleSelectAll,
}: GraphicsTableProps) => {
  const [sortField, setSortField] = useState<SortField>(isArchived ? 'archived_at' : 'updated_at');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const headerCheckboxRef = useRef<HTMLInputElement>(null);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedGraphics = useMemo(() => {
    return [...graphics].sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (sortField) {
        case 'title':
          aValue = a.title?.toLowerCase() || '';
          bValue = b.title?.toLowerCase() || '';
          break;
        case 'event_name':
          aValue = a.event_name?.toLowerCase() || '';
          bValue = b.event_name?.toLowerCase() || '';
          break;
        case 'archived_at':
          aValue = new Date((a as ArchivedGraphic).archived_at ?? a.updated_at);
          bValue = new Date((b as ArchivedGraphic).archived_at ?? b.updated_at);
          break;
        case 'updated_at':
        default:
          aValue = new Date(a.updated_at);
          bValue = new Date(b.updated_at);
          break;
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [graphics, sortField, sortDirection]);

  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);
  const visibleIds = useMemo(() => sortedGraphics.map(graphic => graphic.id), [sortedGraphics]);
  const allVisibleSelected =
    selectable && visibleIds.length > 0 && visibleIds.every(id => selectedSet.has(id));
  const hasPartialSelection =
    selectable && !allVisibleSelected && visibleIds.some(id => selectedSet.has(id));

  useEffect(() => {
    if (headerCheckboxRef.current) {
      headerCheckboxRef.current.indeterminate = hasPartialSelection;
    }
  }, [hasPartialSelection]);

  const formatDate = (value: string | undefined) => {
    if (!value) return '—';
    const date = new Date(value);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getDisplayDate = (graphic: Graphic | ArchivedGraphic) => {
    if (isArchived && 'archived_at' in graphic) {
      return formatDate(graphic.archived_at);
    }
    return formatDate(graphic.updated_at);
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <ChevronUp className="h-4 w-4 text-muted-foreground" />;
    }
    return sortDirection === 'asc' ? (
      <ChevronUp className="h-4 w-4 text-gal-cyan" />
    ) : (
      <ChevronDown className="h-4 w-4 text-gal-cyan" />
    );
  };

  const resolveRestoreHandler = () => onRestore ?? onUnarchive ?? onArchive;
  const showRestoreButton = isArchived && Boolean(resolveRestoreHandler());

  const handleToggleSelectAllInternal = () => {
    if (!selectable || !onToggleSelectAll) return;
    onToggleSelectAll(!allVisibleSelected);
  };

  const renderActionButtons = (graphic: Graphic | ArchivedGraphic) => {
    if (isArchived) {
      return (
        <div className="flex items-center justify-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDuplicate(graphic)}
            className="h-7 w-7 p-0 text-gal-purple hover:text-gal-purple hover:bg-gal-purple/10 gal-glow-purple/30 hover:gal-glow-purple"
            title="Duplicate graphic"
          >
            <Copy className="h-3 w-3" />
            
          </Button>
          {showRestoreButton && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => resolveRestoreHandler()?.(graphic)}
              className="h-7 w-7 p-0 text-gal-success hover:text-gal-success hover:bg-gal-success/10 gal-glow-success/30 hover:gal-glow-success"
              title="Restore to active"
            >
              <RotateCcw className="h-3 w-3" />
              
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(graphic)}
            className="h-7 w-7 p-0 text-gal-error hover:text-gal-error hover:bg-gal-error/10 gal-glow-error/30 hover:gal-glow-error"
            title="Delete graphic"
          >
            <Trash2 className="h-3 w-3" />
            
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onView(graphic)}
            className="h-7 w-7 p-0 text-gal-view hover:text-gal-view hover:bg-gal-view/10 gal-glow-view/30 hover:gal-glow-view"
            title="View in OBS"
          >
            <Eye className="h-3 w-3" />
            
          </Button>
        </div>
      );
    }

    return (
      <div className="flex items-center justify-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onEdit(graphic)}
          className="h-7 w-7 p-0 text-gal-cyan hover:text-gal-cyan hover:bg-gal-cyan/10 gal-glow-cyan/30 hover:gal-glow-cyan"
          title="Edit graphic"
        >
          <Edit className="h-3 w-3" />
          
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onDuplicate(graphic)}
          className="h-7 w-7 p-0 text-gal-purple hover:text-gal-purple hover:bg-gal-purple/10 gal-glow-purple/30 hover:gal-glow-purple"
          title="Duplicate graphic"
        >
          <Copy className="h-3 w-3" />
          
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onArchive(graphic)}
          className="h-7 w-7 p-0 text-gal-amber hover:text-gal-amber hover:bg-gal-amber/10 gal-glow-amber/30 hover:gal-glow-amber"
          title="Archive graphic"
        >
          <ArchiveIcon className="h-3 w-3" />
          
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onDelete(graphic)}
          className="h-7 w-7 p-0 text-gal-error hover:text-gal-error hover:bg-gal-error/10 gal-glow-error/30 hover:gal-glow-error"
          title="Delete graphic"
        >
          <Trash2 className="h-3 w-3" />
          
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onView(graphic)}
          className="h-7 w-7 p-0 text-gal-cyan hover:text-gal-cyan hover:bg-gal-cyan/10 gal-glow-cyan/30 hover:gal-glow-cyan"
          title="View in OBS"
        >
          <Eye className="h-3 w-3" />
          
        </Button>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        <span className="ml-2">Loading graphics...</span>
      </div>
    );
  }

  if (graphics.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500">
          {isArchived ? 'No archived graphics found' : 'No graphics found'}
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse rounded-lg overflow-hidden">
        <thead>
          <tr className="border-b border-border/20 bg-gradient-to-r from-gal-card/50 to-gal-card/30">
            {selectable && (
              <th className="w-12 py-4 px-4">
                <div className="flex items-center justify-center">
                  <input
                    ref={headerCheckboxRef}
                    type="checkbox"
                    checked={allVisibleSelected}
                    onChange={handleToggleSelectAllInternal}
                    aria-label={allVisibleSelected ? 'Deselect all graphics' : 'Select all graphics'}
                    className="h-4 w-4 rounded border-border text-gal-cyan focus:ring-gal-cyan/20 bg-gal-card"
                  />
                </div>
              </th>
            )}
            <th className="text-center py-4 px-4 font-semibold font-montserrat text-gal-text-primary">
              <button
                onClick={() => handleSort('title')}
                className="flex items-center justify-center gap-1 hover:text-gal-cyan transition-colors w-full text-sm"
              >
                Graphic Name
                <SortIcon field="title" />
              </button>
            </th>
            <th className="text-center py-4 px-4 font-semibold font-montserrat text-gal-text-primary">
              <button
                onClick={() => handleSort('event_name')}
                className="flex items-center justify-center gap-1 hover:text-gal-cyan transition-colors w-full text-sm"
              >
                Event Name
                <SortIcon field="event_name" />
              </button>
            </th>
            <th className="text-center py-4 px-4 font-semibold font-montserrat text-gal-text-primary">
              <button
                onClick={() => handleSort(isArchived ? 'archived_at' : 'updated_at')}
                className="flex items-center justify-center gap-1 hover:text-gal-cyan transition-colors w-full text-sm"
              >
                {isArchived ? 'Archive Date' : 'Last Edited'}
                <SortIcon field={isArchived ? 'archived_at' : 'updated_at'} />
              </button>
            </th>
            <th className="text-center py-4 px-4 font-semibold font-montserrat text-gal-text-primary">
              <div className="flex items-center justify-center text-sm">Actions</div>
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedGraphics.map((graphic, index) => {
            const isSelected = selectable && selectedSet.has(graphic.id);
            const rowBorder =
              index === sortedGraphics.length - 1 ? 'border-transparent' : 'border-border/10';

            return (
              <tr
                key={graphic.id}
                className={`border-b ${rowBorder} gal-table-row ${
                  isSelected ? 'selected' : ''
                }`}
              >
                {selectable && (
                  <td className="w-12 py-4 px-4">
                    <div className="flex items-center justify-center">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => onToggleSelect?.(graphic.id)}
                        aria-label={
                          isSelected ? `Deselect ${graphic.title}` : `Select ${graphic.title}`
                        }
                        className="h-4 w-4 rounded border-border text-gal-cyan focus:ring-gal-cyan/20 bg-gal-card"
                      />
                    </div>
                  </td>
                )}
                <td className="text-center py-4 px-4">
                  <div className="font-semibold font-montserrat text-gal-text-primary">
                    {graphic.title}
                  </div>
                </td>
                <td className="text-center py-4 px-4">
                  <div className="font-montserrat text-gal-text-secondary font-medium">
                    {graphic.event_name || <span className="text-muted-foreground italic">No event</span>}
                  </div>
                </td>
                <td className="text-center py-4 px-4">
                  <div className="text-sm font-montserrat text-muted-foreground">
                    {getDisplayDate(graphic)}
                  </div>
                </td>
                <td className="text-center py-4 px-4">{renderActionButtons(graphic)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export const GraphicsTable = memo(GraphicsTableComponent);
