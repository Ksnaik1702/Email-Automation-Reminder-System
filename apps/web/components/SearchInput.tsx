'use client'

import React from 'react'
import { Search, X } from 'lucide-react'

export interface SearchInputProps {
  value: string
  onChange: ((val: string) => void) | ((e: React.ChangeEvent<HTMLInputElement>) => void) | ((val: any) => void)
  onClear?: () => void
  placeholder?: string
  className?: string
}

export default function SearchInput({
  value,
  onChange,
  onClear,
  placeholder = 'Search...',
  className = '',
}: SearchInputProps) {
  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value
    // Provide an object that acts as both a string and an event object
    const hybrid: any = new String(val)
    hybrid.target = { value: val }
    hybrid.currentTarget = { value: val }
    ;(onChange as any)(hybrid)
  }

  function handleClear() {
    if (onClear) {
      onClear()
    } else {
      const hybrid: any = new String('')
      hybrid.target = { value: '' }
      hybrid.currentTarget = { value: '' }
      ;(onChange as any)(hybrid)
    }
  }

  return (
    <div className={`relative flex items-center ${className}`}>
      <Search className="absolute left-3 w-4 h-4 text-slate-400 pointer-events-none" />
      <input
        type="text"
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        className="w-full pl-9 pr-8 py-2 text-sm bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors shadow-xs"
      />
      {value && (
        <button
          type="button"
          onClick={handleClear}
          aria-label="Clear search"
          className="absolute right-2.5 p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  )
}
