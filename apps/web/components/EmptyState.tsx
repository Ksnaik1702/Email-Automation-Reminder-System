'use client'

import React from 'react'
import { LucideIcon, Inbox } from 'lucide-react'
import Button from './Button'

export interface EmptyStateProps {
  title: string
  description?: string
  icon?: LucideIcon
  actionLabel?: string
  onAction?: () => void
  actionIcon?: LucideIcon
}

export default function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
  actionLabel,
  onAction,
  actionIcon,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 sm:p-12 text-center bg-white rounded-xl border border-dashed border-slate-300">
      <div className="flex items-center justify-center w-12 h-12 rounded-full bg-slate-100 text-slate-500 mb-3">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-base font-semibold text-slate-800">{title}</h3>
      {description && (
        <p className="mt-1 text-sm text-slate-500 max-w-sm">{description}</p>
      )}
      {actionLabel && onAction && (
        <div className="mt-4">
          <Button variant="primary" size="sm" onClick={onAction} icon={actionIcon}>
            {actionLabel}
          </Button>
        </div>
      )}
    </div>
  )
}
