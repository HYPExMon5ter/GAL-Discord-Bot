"use client"

import * as React from "react"
import { Check, ChevronsUpDown, Plus } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { cn } from "@/lib/utils"

interface ComboboxProps {
  value: string
  onValueChange: (value: string) => void
  options: string[]
  placeholder?: string
  emptyText?: string
  createText?: string
  disabled?: boolean
  className?: string
}

export function Combobox({
  value,
  onValueChange,
  options,
  placeholder = "Select...",
  emptyText = "No results found.",
  createText = "Create",
  disabled = false,
  className,
}: ComboboxProps) {
  const [open, setOpen] = React.useState(false)
  const [search, setSearch] = React.useState("")
  const triggerRef = React.useRef<HTMLButtonElement>(null)
  const inputRef = React.useRef<HTMLInputElement>(null)
  const [triggerWidth, setTriggerWidth] = React.useState<number>(0)

  React.useEffect(() => {
    if (triggerRef.current) {
      setTriggerWidth(triggerRef.current.offsetWidth)
    }
  }, [open])

  // Auto-focus input when dropdown opens
  React.useEffect(() => {
    if (open && inputRef.current) {
      // Delay to ensure popover is fully rendered
      setTimeout(() => {
        inputRef.current?.focus()
      }, 50)
    }
  }, [open])

  const filteredOptions = options.filter(option =>
    option.toLowerCase().includes(search.toLowerCase())
  )

  const handleSelect = (selectedValue: string) => {
    onValueChange(selectedValue)
    setOpen(false)
    setSearch("")
  }

  const handleCreateNew = () => {
    if (search.trim()) {
      onValueChange(search.trim())
      setOpen(false)
      setSearch("")
    }
  }

  return (
    <Popover open={open} onOpenChange={setOpen} modal={false}>
      <PopoverTrigger asChild>
        <Button
          ref={triggerRef}
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className={cn("w-full justify-between font-normal", className)}
        >
          {value || placeholder}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent 
        className="p-0 z-[70]" 
        align="start"
        style={{ width: triggerWidth }}
        onInteractOutside={(e) => {
          // Don't close if clicking inside the popover content or the input
          const target = e.target as HTMLElement;
          const isInput = target.tagName === 'INPUT';
          const isInsideContent = e.currentTarget.contains(target);
          
          if (isInput || isInsideContent) {
            e.preventDefault()
          }
        }}
        // Prevent focus trap issues
        onOpenAutoFocus={(e) => {
          e.preventDefault()
          // Manually focus the input after popover opens
          setTimeout(() => {
            inputRef.current?.focus()
          }, 50)
        }}
      >
        <div className="p-2">
          <Input
            ref={inputRef}
            placeholder="Search or create..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && search.trim() && !options.includes(search.trim())) {
                e.preventDefault()
                handleCreateNew()
              }
              // Allow Escape to close
              if (e.key === 'Escape') {
                setOpen(false)
              }
            }}
            className="h-9"
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
          />
        </div>
        <div className="max-h-[300px] overflow-y-auto gal-scrollbar">
          {filteredOptions.length > 0 ? (
            <div className="p-1">
              {filteredOptions.map((option) => (
                <div
                  key={option}
                  onClick={() => handleSelect(option)}
                  className={cn(
                    "flex items-center px-2 py-1.5 text-sm rounded cursor-pointer hover:bg-accent transition-colors",
                    value === option && "bg-accent"
                  )}
                >
                  <Check
                    className={cn(
                      "mr-2 h-4 w-4",
                      value === option ? "opacity-100" : "opacity-0"
                    )}
                  />
                  {option}
                </div>
              ))}
            </div>
          ) : (
            <div className="p-2 text-sm text-muted-foreground text-center">
              {emptyText}
            </div>
          )}
          {search.trim() && !options.includes(search.trim()) && (
            <div className="border-t p-1">
              <div
                onClick={handleCreateNew}
                className="flex items-center px-2 py-1.5 text-sm rounded cursor-pointer hover:bg-accent text-primary transition-colors"
              >
                <Plus className="mr-2 h-4 w-4" />
                {createText} "{search.trim()}"
              </div>
            </div>
          )}
        </div>
      </PopoverContent>
    </Popover>
  )
}
