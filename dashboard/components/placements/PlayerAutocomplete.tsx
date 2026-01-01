import React, { useState, useEffect } from 'react';
import { Check, ChevronsUpDown, User } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from '@/components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Badge } from '@/components/ui/badge';

interface Player {
  id: string;
  name: string;
  aliases?: string[];
  match_confidence?: number;
}

interface PlayerAutocompleteProps {
  value?: string;
  onValueChange: (playerId: string, playerName: string) => void;
  players: Player[];
  onSearch?: (query: string) => void;
  placeholder?: string;
  matchConfidence?: number;
}

export function PlayerAutocomplete({
  value,
  onValueChange,
  players,
  onSearch,
  placeholder = 'Select player...',
  matchConfidence,
}: PlayerAutocompleteProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');

  // Get selected player
  const selectedPlayer = players.find(p => p.id === value);

  // Handle search with debounce
  useEffect(() => {
    if (onSearch && search.length > 0) {
      const timer = setTimeout(() => {
        onSearch(search);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [search, onSearch]);

  // Get confidence badge color
  const getConfidenceBadge = (confidence?: number) => {
    if (!confidence) return null;
    
    if (confidence >= 0.95) {
      return <Badge variant="outline" className="ml-2 border-green-500 text-green-700 bg-green-50 dark:bg-green-950">🟢 Exact</Badge>;
    }
    if (confidence >= 0.7) {
      return <Badge variant="outline" className="ml-2 border-yellow-500 text-yellow-700 bg-yellow-50 dark:bg-yellow-950">🟡 Fuzzy</Badge>;
    }
    return <Badge variant="outline" className="ml-2 border-red-500 text-red-700 bg-red-50 dark:bg-red-950">🔴 No Match</Badge>;
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between"
        >
          <div className="flex items-center gap-2 truncate">
            <User className="h-4 w-4 text-muted-foreground flex-shrink-0" />
            {selectedPlayer ? (
              <span className="truncate">{selectedPlayer.name}</span>
            ) : (
              <span className="text-muted-foreground">{placeholder}</span>
            )}
          </div>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[400px] p-0">
        <Command shouldFilter={!onSearch}>
          <CommandInput
            placeholder="Search players..."
            value={search}
            onValueChange={setSearch}
          />
          <CommandEmpty>No player found.</CommandEmpty>
          <CommandGroup className="max-h-64 overflow-auto">
            {players.map((player) => (
              <CommandItem
                key={player.id}
                value={player.id}
                onSelect={() => {
                  onValueChange(player.id, player.name);
                  setOpen(false);
                }}
                className="flex items-center justify-between"
              >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <Check
                    className={cn(
                      'mr-2 h-4 w-4 flex-shrink-0',
                      value === player.id ? 'opacity-100' : 'opacity-0'
                    )}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{player.name}</div>
                    {player.aliases && player.aliases.length > 0 && (
                      <div className="text-xs text-muted-foreground truncate">
                        Aliases: {player.aliases.join(', ')}
                      </div>
                    )}
                  </div>
                </div>
                {player.match_confidence !== undefined && (
                  <div className="flex-shrink-0 text-xs text-muted-foreground ml-2">
                    {Math.round(player.match_confidence * 100)}%
                  </div>
                )}
              </CommandItem>
            ))}
          </CommandGroup>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
