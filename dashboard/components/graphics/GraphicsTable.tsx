'use client';

import { useState, useMemo, memo } from 'react';
import { Graphic, ArchivedGraphic } from '@/types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  ChevronUp, 
  ChevronDown, 
  Edit, 
  Copy, 
  Archive, 
  Trash2, 
  Eye,
  RotateCcw,
  ExternalLink 
} from 'lucide-react';

interface GraphicsTableProps {
  graphics: Graphic[] | ArchivedGraphic[];
  loading: boolean;
  onEdit: (graphic: Graphic | ArchivedGraphic) => void;
  onDuplicate: (graphic: Graphic | ArchivedGraphic) => void;
  onArchive: (graphic: Graphic | ArchivedGraphic) => void;
  onDelete: (graphic: Graphic | ArchivedGraphic) => void;
  onView: (graphic: Graphic | ArchivedGraphic) => void;
  onUnarchive?: (graphic: Graphic | ArchivedGraphic) => void;
  onRestore?: (graphic: Graphic | ArchivedGraphic) => void;
  isArchived?: boolean;
}

type SortField = 'title' | 'event_name' | 'updated_at' | 'archived_at';
type SortDirection = 'asc' | 'desc';

const GraphicsTableComponent = function GraphicsTable({ 
  graphics, 
  loading, 
  onEdit, 
  onDuplicate, 
  onArchive, 
  onDelete, 
  onView,
  onUnarchive,
  onRestore,
  isArchived = false 
}: GraphicsTableProps) {
  const [sortField, setSortField] = useState<SortField>('updated_at');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

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

        case 'updated_at':
          aValue = new Date(a.updated_at);
          bValue = new Date(b.updated_at);
          break;
        case 'archived_at':
          aValue = new Date((a as ArchivedGraphic).archived_at || a.updated_at);
          bValue = new Date((b as ArchivedGraphic).archived_at || b.updated_at);
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [graphics, sortField, sortDirection]);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getDisplayDate = (graphic: Graphic | ArchivedGraphic) => {
    if (isArchived && (graphic as ArchivedGraphic).archived_at) {
      return formatDate((graphic as ArchivedGraphic).archived_at);
    }
    return formatDate(graphic.updated_at);
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <ChevronUp className="h-4 w-4 text-gray-400" />;
    }
    return sortDirection === 'asc' ? (
      <ChevronUp className="h-4 w-4 text-blue-600" />
    ) : (
      <ChevronDown className="h-4 w-4 text-blue-600" />
    );
  };

  const ActionButtons = ({ graphic }: { graphic: Graphic | ArchivedGraphic }) => {
    if (isArchived) {
      return (
        <div className="flex items-center justify-center gap-1 flex-wrap">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDuplicate(graphic)}
            className="h-8 px-2 text-purple-600 hover:text-purple-700 hover:bg-purple-50"
            title="Duplicate graphic"
          >
            <Copy className="h-3 w-3 mr-1" />
            <span className="text-xs">Copy</span>
          </Button>
          {onUnarchive && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onUnarchive(graphic)}
              className="h-8 px-2 text-green-600 hover:text-green-700 hover:bg-green-50"
              title="Restore to active"
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              <span className="text-xs">Unarchive</span>
            </Button>
          )}
          {onRestore && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onRestore(graphic)}
              className="h-8 px-2 text-green-600 hover:text-green-700 hover:bg-green-50"
              title="Restore to active"
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              <span className="text-xs">Restore</span>
            </Button>
          )}
          {onArchive && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onArchive(graphic)}
              className="h-8 px-2 text-green-600 hover:text-green-700 hover:bg-green-50"
              title="Restore to active"
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              <span className="text-xs">Restore</span>
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(graphic)}
            className="h-8 px-2 text-red-600 hover:text-red-700 hover:bg-red-50"
            title="Delete graphic"
          >
            <Trash2 className="h-3 w-3 mr-1" />
            <span className="text-xs">Delete</span>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onView(graphic)}
            className="h-8 px-2 text-blue-600 hover:text-blue-700 hover:bg-blue-50"
            title="View in OBS"
          >
            <Eye className="h-3 w-3 mr-1" />
            <span className="text-xs">View</span>
          </Button>
        </div>
      );
    }

    return (
      <div className="flex items-center justify-center gap-1 flex-wrap">
        {/* Edit button - only show for active graphics */}
        {!isArchived && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onEdit(graphic)}
            className="h-8 px-2 text-blue-600 hover:text-blue-700 hover:bg-blue-50"
            title="Edit graphic"
          >
            <Edit className="h-3 w-3 mr-1" />
            <span className="text-xs">Edit</span>
          </Button>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onDuplicate(graphic)}
          className="h-8 px-2 text-purple-600 hover:text-purple-700 hover:bg-purple-50"
          title="Duplicate graphic"
        >
          <Copy className="h-3 w-3 mr-1" />
          <span className="text-xs">Copy</span>
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onArchive(graphic)}
          className="h-8 px-2 text-green-600 hover:text-green-700 hover:bg-green-50"
          title={isArchived ? "Restore to active" : "Archive graphic"}
        >
          {isArchived ? (
            <>
              <RotateCcw className="h-3 w-3 mr-1" />
              <span className="text-xs">Restore</span>
            </>
          ) : (
            <>
              <Archive className="h-3 w-3 mr-1" />
              <span className="text-xs">Archive</span>
            </>
          )}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onDelete(graphic)}
          className="h-8 px-2 text-red-600 hover:text-red-700 hover:bg-red-50"
          title="Delete graphic"
        >
          <Trash2 className="h-3 w-3 mr-1" />
          <span className="text-xs">Delete</span>
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onView(graphic)}
          className="h-8 px-2 text-blue-600 hover:text-blue-700 hover:bg-blue-50"
          title="View in OBS"
        >
          <Eye className="h-3 w-3 mr-1" />
          <span className="text-xs">View</span>
        </Button>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
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
          <tr className="border-b border-gray-200 bg-gradient-to-r from-gray-50 to-gray-100">
            <th className="text-center py-4 px-4 font-semibold text-gray-800">
              <button
                onClick={() => handleSort('title')}
                className="flex items-center justify-center gap-1 hover:text-blue-600 transition-colors w-full text-sm"
              >
                Graphic Name
                <SortIcon field="title" />
              </button>
            </th>
            <th className="text-center py-4 px-4 font-semibold text-gray-800">
              <button
                onClick={() => handleSort('event_name')}
                className="flex items-center justify-center gap-1 hover:text-blue-600 transition-colors w-full text-sm"
              >
                Event Name
                <SortIcon field="event_name" />
              </button>
            </th>
            <th className="text-center py-4 px-4 font-semibold text-gray-800">
              <button
                onClick={() => handleSort(isArchived ? 'archived_at' : 'updated_at')}
                className="flex items-center justify-center gap-1 hover:text-blue-600 transition-colors w-full text-sm"
              >
                {isArchived ? 'Archive Date' : 'Last Edited'}
                <SortIcon field={isArchived ? 'archived_at' : 'updated_at'} />
              </button>
            </th>

            <th className="text-center py-4 px-4 font-semibold text-gray-800">
              <div className="flex items-center justify-center text-sm">
                Actions
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedGraphics.map((graphic, index) => (
            <tr 
              key={graphic.id} 
              className={`border-b ${index === sortedGraphics.length - 1 ? 'border-transparent' : 'border-gray-100'}`}
            >
              <td className="text-center py-4 px-4">
                <div className="font-semibold text-gray-100">{graphic.title}</div>
              </td>
              <td className="text-center py-4 px-4">
                <div className="text-gray-200 font-medium">
                  {graphic.event_name || <span className="text-gray-400 italic">No event</span>}
                </div>
              </td>
              <td className="text-center py-4 px-4">
                <div className="text-sm text-gray-300">
                  {getDisplayDate(graphic)}
                </div>
              </td>

              <td className="text-center py-4 px-4">
                <ActionButtons graphic={graphic} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export const GraphicsTable = memo(GraphicsTableComponent);
