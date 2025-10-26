import { useState, useEffect, useCallback } from 'react';
import type { PlayerData } from '@/lib/canvas/types';
import api from '@/lib/api';

interface TournamentDataState {
  players: PlayerData[];
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
}

interface FetchOptions {
  sortBy?: 'total_points' | 'player_name' | 'standing_rank';
  sortOrder?: 'asc' | 'desc';
  limit?: number;
  roundId?: string;
}

export function useTournamentData(options: FetchOptions = {}) {
  const [state, setState] = useState<TournamentDataState>({
    players: [],
    loading: false,
    error: null,
    lastUpdated: null,
  });

  // Fetch tournament data
  const fetchData = useCallback(async (fetchOptions: FetchOptions = {}) => {
    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const params = new URLSearchParams();
      
      if (fetchOptions.sortBy) params.append('sortBy', fetchOptions.sortBy);
      if (fetchOptions.sortOrder) params.append('sortOrder', fetchOptions.sortOrder);
      if (fetchOptions.limit) params.append('limit', fetchOptions.limit.toString());
      if (fetchOptions.roundId && fetchOptions.roundId !== 'total') {
        params.append('roundId', fetchOptions.roundId);
      }

        const response = await api.get(`/players/ranked?${params.toString()}`);
      
      if (response && response.data && response.data.players) {
        setState(prev => ({
          ...prev,
          players: response.data.players,
          loading: false,
          lastUpdated: new Date(),
        }));
      } else {
        throw new Error('No player data available');
      }
    } catch (error) {
      console.error('Failed to fetch tournament data:', error);
      setState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      }));{
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      }));
    }
  }, []);

  // Initial data fetch
  useEffect(() => {
    fetchData(options);
  }, []); // Only fetch on mount

  // Refresh data
  const refresh = useCallback(() => {
    return fetchData(options);
  }, [fetchData, options]);

  // Get filtered/sorted players
  const getPlayers = useCallback((filterOptions: FetchOptions = {}) => {
    let filteredPlayers = [...state.players];

    // Apply round filtering if specified
    if (filterOptions.roundId && filterOptions.roundId !== 'total') {
      // This would need backend support for round-specific filtering
      // For now, return all players (round-specific handled in component)
    }

    // Apply sorting if different from current options
    const sortBy = filterOptions.sortBy || options.sortBy || 'total_points';
    const sortOrder = filterOptions.sortOrder || options.sortOrder || 'desc';

    filteredPlayers.sort((a, b) => {
      let aValue: number | string;
      let bValue: number | string;

      switch (sortBy) {
        case 'player_name':
          aValue = a.player_name.toLowerCase();
          bValue = b.player_name.toLowerCase();
          break;
        case 'standing_rank':
          aValue = a.standing_rank;
          bValue = b.standing_rank;
          break;
        case 'total_points':
        default:
          aValue = a.total_points;
          bValue = b.total_points;
          break;
      }

      let comparison = 0;
      if (aValue < bValue) comparison = -1;
      else if (aValue > bValue) comparison = 1;

      return sortOrder === 'asc' ? comparison : -comparison;
    });

    // Apply limit
    if (filterOptions.limit || options.limit) {
      const limit = filterOptions.limit || options.limit;
      filteredPlayers = filteredPlayers.slice(0, limit);
    }

    return filteredPlayers;
  }, [state.players, options]);

  // Get player count
  const getPlayerCount = useCallback(() => {
    return state.players.length;
  }, [state.players]);

  return {
    // State
    players: state.players,
    loading: state.loading,
    error: state.error,
    lastUpdated: state.lastUpdated,

    // Actions
    refresh,
    getPlayers,
    getPlayerCount,
    fetchData, // For custom fetching
  };
}
