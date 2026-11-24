'use client'

import React from 'react'
import { LucideIcon, Loader2 } from 'lucide-react'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'success' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  icon?: LucideIcon | React.ReactNode
  iconPosition?: 'left' | 'right'
  loading?: boolean
  children?: React.ReactNode
}

export default function Button({
  variant = 'primary',
  size = 'md',
  icon,
  iconPosition = 'left',
  loading = false,
  disabled = false,
  className = '',
  children,
  ...props
}: ButtonProps) {
  const baseClasses =
    'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed select-none'

  const sizeClasses = {
    sm: 'text-xs px-2.5 py-1.5 gap-1.5',
    md: 'text-sm px-4 py-2 gap-2',
    lg: 'text-base px-5 py-2.5 gap-2.5',
  }[size]

  const variantClasses = {
    primary:
      'bg-indigo-600 text-white hover:bg-indigo-700 active:bg-indigo-800 shadow-sm shadow-indigo-600/30 focus:ring-indigo-500',
    secondary:
      'bg-white text-slate-700 hover:bg-slate-50 active:bg-slate-100 border border-slate-200 shadow-xs focus:ring-slate-400',
    outline:
      'bg-transparent text-indigo-600 hover:bg-indigo-50 border border-indigo-200 focus:ring-indigo-500',
    danger:
      'bg-rose-600 text-white hover:bg-rose-700 active:bg-rose-800 shadow-sm shadow-rose-600/30 focus:ring-rose-500',
    success:
      'bg-emerald-600 text-white hover:bg-emerald-700 active:bg-emerald-800 shadow-sm shadow-emerald-600/30 focus:ring-emerald-500',
    ghost:
      'bg-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus:ring-slate-400',
  }[variant]

  const renderIcon = () => {
    if (!icon) return null
    if (React.isValidElement(icon)) return icon
    const IconComponent = icon as LucideIcon
    return <IconComponent className={size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4'} />
  }

  return (
    <button
      disabled={disabled || loading}
      className={`${baseClasses} ${sizeClasses} ${variantClasses} ${className}`}
      {...props}
    >
      {loading ? (
        <Loader2 className={`animate-spin ${size === 'sm' ? 'w-3 h-3' : 'w-4 h-4'}`} />
      ) : icon && iconPosition === 'left' ? (
        renderIcon()
      ) : null}

      {children}

      {!loading && icon && iconPosition === 'right' ? (
        renderIcon()
      ) : null}
    </button>
  )
}
