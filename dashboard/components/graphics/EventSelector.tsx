"use client"

import React, { useEffect, useState, useRef } from "react"
import { cn } from "@/lib/utils"
import { Check, ChevronDown } from "lucide-react"
import api from "@/lib/api"

interface EventSelectorProps {
  value: string
  onValueChange: (value: string) => void
  disabled?: boolean
  className?: string
  graphicTitle?: string
  onSubmit?: () => void
}

export function EventSelector({
  value,
  onValueChange,
  disabled = false,
  className,
  graphicTitle,
  onSubmit,
}: EventSelectorProps) {
  const [events, setEvents] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState(value)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

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

  useEffect(() => {
    setSearch(value)
  }, [value])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const filteredEvents = events.filter(event =>
    event.toLowerCase().includes(search.toLowerCase())
  )

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value
    setSearch(newValue)
    onValueChange(newValue)
    setIsOpen(true)
  }

  const handleInputFocus = () => {
    // Don't open if disabled or loading
    if (!disabled && !loading) {
      setIsOpen(true)
    }
  }

  const handleSelectEvent = (event: string) => {
    setSearch(event)
    onValueChange(event)
    setIsOpen(false)
    // Focus back to input after selection
    setTimeout(() => {
      inputRef.current?.focus()
    }, 10)
  }

  const handleInputClick = (e: React.MouseEvent) => {
    e.preventDefault()
    // Only open if closed, don't close if already open
    if (!disabled && !loading && !isOpen) {
      setIsOpen(true)
    }
  }

  const isCreatingNew = search && !events.includes(search)

  return (
    <div className="w-full relative" ref={dropdownRef}>
      <div className="relative">
        <input
          ref={inputRef}
          value={search}
          onChange={handleInputChange}
          onClick={handleInputClick}
          onFocus={handleInputFocus}
          placeholder={loading ? 'Loading events...' : 'Type or select event name...'}
          disabled={disabled || loading}
          className={cn(
            "w-full h-10 rounded-md border border-input bg-background px-3 py-2 pr-10 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
            className
          )}
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
        />
        <ChevronDown 
          className={cn(
            "absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground transition-transform",
            isOpen && "rotate-180"
          )}
        />
      </div>

      {/* Custom Dropdown */}
      {isOpen && (
        <div className="absolute z-[9999] w-full mt-1 max-h-60 overflow-auto rounded-md border bg-popover text-popover-foreground shadow-lg">
          {loading ? (
            <div className="p-2 text-sm text-muted-foreground">
              Loading events...
            </div>
          ) : error ? (
            <div className="p-2 text-sm text-destructive">
              {error}
            </div>
          ) : filteredEvents.length > 0 ? (
            <div className="py-1">
              {filteredEvents.map(event => (
                <div
                  key={event}
                  onMouseDown={(e) => {
                    e.preventDefault()
                    handleSelectEvent(event)
                  }}
                  className="flex items-center px-2 py-1.5 text-sm cursor-pointer hover:bg-accent hover:text-accent-foreground transition-colors"
                >
                  <Check 
                    className={cn(
                      "mr-2 h-4 w-4",
                      value === event ? "opacity-100" : "opacity-0"
                    )}
                  />
                  {event}
                </div>
              ))}
            </div>
          ) : (
            <div className="p-2 text-sm text-muted-foreground">
              {search ? "No matching events. Create a new one?" : "No events found"}
            </div>
          )}
          
          {/* Create new option when typing something not in the list */}
          {isCreatingNew && (
            <div className="border-t border-border py-1">
              <div
                onMouseDown={(e) => {
                  e.preventDefault()
                  setIsOpen(false)
                  // If graphic title is present, auto-submit the form
                  if (graphicTitle && graphicTitle.trim() && onSubmit) {
                    onSubmit()
                  }
                }}
                className="flex items-center px-2 py-1.5 text-sm cursor-pointer hover:bg-accent hover:text-accent-foreground text-primary transition-colors"
              >
                <span className="mr-2">✨</span>
                Create new: &quot;{search}&quot;
              </div>
            </div>
          )}
        </div>
      )}

      {/* Status messages */}
      {value && !events.includes(value) && (
        <p className="text-xs text-primary mt-1">
          ✨ Creating new event: &quot;{value}&quot;
        </p>
      )}
    </div>
  )
}
