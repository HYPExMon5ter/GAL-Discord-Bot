import React, { useState, createContext, useContext, useEffect, useRef } from 'react';

// Context for managing select state
const SelectContext = createContext<{
  value?: string;
  onValueChange?: (value: string) => void;
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  disabled?: boolean;
}>({
  isOpen: false,
  setIsOpen: () => {}
});

interface SelectProps {
  children: React.ReactNode;
  value?: string;
  onValueChange?: (value: string) => void;
  disabled?: boolean;
}

interface SelectTriggerProps {
  children: React.ReactNode;
  className?: string;
}

interface SelectContentProps {
  children: React.ReactNode;
  className?: string;
}

interface SelectItemProps {
  value: string;
  children: React.ReactNode;
  disabled?: boolean;
  className?: string;
}

interface SelectValueProps {
  placeholder?: string;
}

export function Select({ children, value, onValueChange, disabled }: SelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  
  return (
    <SelectContext.Provider value={{ value, onValueChange, isOpen, setIsOpen, disabled }}>
      <div className="relative">
        {children}
      </div>
    </SelectContext.Provider>
  );
}

export function SelectTrigger({ children, className = '' }: SelectTriggerProps) {
  const { isOpen, setIsOpen, disabled } = useContext(SelectContext);
  
  return (
    <button
      type="button"
      data-select-trigger
      className={`flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus:border-primary disabled:cursor-not-allowed disabled:opacity-50 hover:bg-accent hover:text-accent-foreground ${className}`}
      onClick={() => setIsOpen(!isOpen)}
      disabled={disabled}
    >
      {children}
      <svg 
        className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} 
        fill="none" 
        stroke="currentColor" 
        viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    </button>
  );
}

export function SelectContent({ children, className = '' }: SelectContentProps) {
  const { isOpen, setIsOpen } = useContext(SelectContext);
  const contentRef = useRef<HTMLDivElement>(null);
  
  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      // Don't close if clicking inside the select content or trigger
      const target = event.target as Element;
      if (contentRef.current && !contentRef.current.contains(target)) {
        // Check if the clicked element is a select trigger
        const selectTrigger = target.closest('[data-select-trigger]');
        if (!selectTrigger) {
          setIsOpen(false);
        }
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, setIsOpen]);
  
  if (!isOpen) return null;
  
  return (
    <div 
      ref={contentRef}
      className={`absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-md border bg-popover text-popover-foreground ${className}`}
    >
      <div className="py-1">
        {children}
      </div>
    </div>
  );
}

export function SelectItem({ value: itemValue, children, disabled, className = '' }: SelectItemProps) {
  const { value, onValueChange, setIsOpen } = useContext(SelectContext);
  const isSelected = value === itemValue;
  
  return (
    <div
      className={`relative flex cursor-default select-none items-center py-1.5 pl-8 pr-2 text-sm outline-none hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground disabled:cursor-not-allowed disabled:opacity-50 ${
        isSelected ? 'bg-accent text-accent-foreground' : ''
      } ${disabled ? 'opacity-50' : ''} ${className}`}
      onClick={() => {
        if (!disabled && onValueChange) {
          onValueChange(itemValue);
          setIsOpen(false);
        }
      }}
    >
      {isSelected && (
        <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </span>
      )}
      {children}
    </div>
  );
}

export function SelectValue({ placeholder }: SelectValueProps) {
  const { value } = useContext(SelectContext);
  
  // Handle case where value might be an object (like dataBinding)
  const displayValue = typeof value === 'string' ? value : '';
  
  return (
    <span className="block truncate">
      {displayValue || <span className="text-muted-foreground">{placeholder}</span>}
    </span>
  );
}
