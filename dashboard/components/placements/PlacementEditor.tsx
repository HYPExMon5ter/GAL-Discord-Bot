import React, { useState, useEffect } from 'react';
import { PlayerAutocomplete } from './PlayerAutocomplete';
import { AlertCircle } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';

interface Placement {
  id?: number;
  player_id?: string;
  player_name: string;
  placement: number;
  points: number;
  match_method?: string;
  validated?: boolean;
}

interface Player {
  id: string;
  name: string;
  aliases?: string[];
  match_confidence?: number;
}

interface PlacementEditorProps {
  placements: Placement[];
  availablePlayers: Player[];
  onChange: (placements: Placement[]) => void;
  onSearchPlayers?: (query: string) => void;
  editable?: boolean;
}

// Points mapping for TFT placements
const POINTS_MAP: { [key: number]: number } = {
  1: 8,
  2: 7,
  3: 6,
  4: 5,
  5: 4,
  6: 3,
  7: 2,
  8: 1,
};

export function PlacementEditor({
  placements,
  availablePlayers,
  onChange,
  onSearchPlayers,
  editable = true,
}: PlacementEditorProps) {
  const [editablePlacements, setEditablePlacements] = useState<Placement[]>(placements);
  const [issues, setIssues] = useState<{ [key: number]: string[] }>({});

  // Update local state when placements prop changes
  useEffect(() => {
    setEditablePlacements(placements);
  }, [placements]);

  // Validate placements
  useEffect(() => {
    const newIssues: { [key: number]: string[] } = {};

    // Check for duplicate players
    const playerIds = editablePlacements
      .map(p => p.player_id)
      .filter(id => id);
    
    const duplicates = playerIds.filter(
      (id, index) => playerIds.indexOf(id) !== index
    );

    // Check for missing placements
    const placementNumbers = editablePlacements.map(p => p.placement);
    const expectedPlacements = Array.from({ length: 8 }, (_, i) => i + 1);
    const missingPlacements = expectedPlacements.filter(
      p => !placementNumbers.includes(p)
    );

    editablePlacements.forEach((placement, index) => {
      const placementIssues: string[] = [];

      // Check for duplicate player
      if (placement.player_id && duplicates.includes(placement.player_id)) {
        placementIssues.push('Duplicate player');
      }

      // Check if player name is empty
      if (!placement.player_name || placement.player_name.trim() === '') {
        placementIssues.push('Missing player name');
      }

      if (placementIssues.length > 0) {
        newIssues[index] = placementIssues;
      }
    });

    setIssues(newIssues);
  }, [editablePlacements]);

  const handlePlayerChange = (index: number, playerId: string, playerName: string) => {
    const updated = [...editablePlacements];
    updated[index] = {
      ...updated[index],
      player_id: playerId,
      player_name: playerName,
      match_method: 'manual',
    };
    setEditablePlacements(updated);
    onChange(updated);
  };

  // Get match confidence badge
  const getMatchBadge = (placement: Placement) => {
    if (!placement.match_method) return null;

    if (placement.match_method === 'exact') {
      return (
        <Badge variant="outline" className="border-green-500 text-green-700 bg-green-50 dark:bg-green-950">
          Exact
        </Badge>
      );
    }
    if (placement.match_method === 'alias') {
      return (
        <Badge variant="outline" className="border-blue-500 text-blue-700 bg-blue-50 dark:bg-blue-950">
          Alias
        </Badge>
      );
    }
    if (placement.match_method === 'fuzzy') {
      return (
        <Badge variant="outline" className="border-yellow-500 text-yellow-700 bg-yellow-50 dark:bg-yellow-950">
          Fuzzy
        </Badge>
      );
    }
    if (placement.match_method === 'manual') {
      return (
        <Badge variant="outline" className="border-purple-500 text-purple-700 bg-purple-50 dark:bg-purple-950">
          Manual
        </Badge>
      );
    }
    return null;
  };

  return (
    <div className="space-y-4">
      {/* Validation issues summary */}
      {Object.keys(issues).length > 0 && (
        <div className="rounded-lg border border-yellow-500 bg-yellow-50 dark:bg-yellow-950 p-4">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-semibold text-yellow-800 dark:text-yellow-200 mb-1">
                Validation Issues
              </h4>
              <ul className="text-sm text-yellow-700 dark:text-yellow-300 space-y-1">
                {Object.entries(issues).map(([index, issueList]) => (
                  <li key={index}>
                    Placement {editablePlacements[Number(index)].placement}: {issueList.join(', ')}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Placements table */}
      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-24">Placement</TableHead>
              <TableHead>Player</TableHead>
              <TableHead className="w-32">Match Type</TableHead>
              <TableHead className="w-24 text-right">Points</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {editablePlacements.map((placement, index) => (
              <TableRow 
                key={index}
                className={issues[index] ? 'bg-yellow-50 dark:bg-yellow-950/20' : ''}
              >
                <TableCell className="font-semibold text-center">
                  {placement.placement}
                </TableCell>
                <TableCell>
                  {editable ? (
                    <PlayerAutocomplete
                      value={placement.player_id}
                      onValueChange={(playerId, playerName) =>
                        handlePlayerChange(index, playerId, playerName)
                      }
                      players={availablePlayers}
                      onSearch={onSearchPlayers}
                      placeholder="Select player..."
                    />
                  ) : (
                    <span className="font-medium">{placement.player_name}</span>
                  )}
                  {issues[index] && (
                    <div className="flex items-center gap-1 text-xs text-yellow-600 dark:text-yellow-400 mt-1">
                      <AlertCircle className="h-3 w-3" />
                      {issues[index].join(', ')}
                    </div>
                  )}
                </TableCell>
                <TableCell>{getMatchBadge(placement)}</TableCell>
                <TableCell className="text-right font-semibold">
                  {placement.points}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Stats summary */}
      <div className="grid grid-cols-3 gap-4 text-sm">
        <div className="rounded-lg border p-3">
          <div className="text-muted-foreground mb-1">Total Players</div>
          <div className="text-2xl font-bold">{editablePlacements.length}</div>
        </div>
        <div className="rounded-lg border p-3">
          <div className="text-muted-foreground mb-1">Total Points</div>
          <div className="text-2xl font-bold">
            {editablePlacements.reduce((sum, p) => sum + p.points, 0)}
          </div>
        </div>
        <div className="rounded-lg border p-3">
          <div className="text-muted-foreground mb-1">Issues</div>
          <div className={`text-2xl font-bold ${Object.keys(issues).length > 0 ? 'text-yellow-600 dark:text-yellow-400' : 'text-green-600 dark:text-green-400'}`}>
            {Object.keys(issues).length}
          </div>
        </div>
      </div>
    </div>
  );
}
