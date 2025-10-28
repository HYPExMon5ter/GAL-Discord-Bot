"use client"

import React, { useEffect, useState } from "react"
import { Combobox } from "@/components/ui/combobox"
import api from "@/lib/api"

interface EventSelectorProps {
  value: string
  onValueChange: (value: string) => void
  disabled?: boolean
  className?: string
}

export function EventSelector({
  value,
  onValueChange,
  disabled = false,
  className,
}: EventSelectorProps) {
  const [events, setEvents] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        setError(null)
        const response = await api.get('/events')
        setEvents(response.data || [])
      } catch (error: any) {
        console.error('Failed to fetch events:', error)
        setError('Failed to load events')
        setEvents([])
      } finally {
        setLoading(false)
      }
    }

    fetchEvents()
  }, [])

  if (error) {
    // Fallback to basic input if events fail to load
    return (
      <div className="w-full">
        <input
          type="text"
          value={value}
          onChange={(e) => onValueChange(e.target.value)}
          placeholder="Enter event name..."
          disabled={disabled}
          className="w-full flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        />
        {error && (
          <p className="text-xs text-destructive mt-1">
            Using manual input - {error}
          </p>
        )}
      </div>
    )
  }

  return (
    <Combobox
      value={value}
      onValueChange={onValueChange}
      options={events}
      placeholder={loading ? 'Loading events...' : 'Select or create event...'}
      emptyText="No events found. Type to create a new one."
      createText="Create event"
      disabled={disabled || loading}
      className={className}
    />
  )
}
