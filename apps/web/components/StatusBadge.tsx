'use client'

import React from 'react'
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  XCircle,
  HelpCircle,
  UserX,
  Send,
  Sparkles,
  ShieldCheck
} from 'lucide-react'

export interface StatusBadgeProps {
  status: string
  size?: 'sm' | 'md'
  showIcon?: boolean
}

export default function StatusBadge({ status, size = 'md', showIcon = true }: StatusBadgeProps) {
  const norm = (status || '').toUpperCase().trim()

  let bg = 'bg-slate-100'
  let text = 'text-slate-700'
  let border = 'border-slate-200'
  let label = status || 'Unknown'
  let Icon = HelpCircle

  switch (norm) {
    case 'SIMULATED_SUCCESS':
      bg = 'bg-emerald-50'
      text = 'text-emerald-700'
      border = 'border-emerald-200'
      label = 'Simulated'
      Icon = Sparkles
      break
    case 'SMTP_ACCEPTED':
      bg = 'bg-blue-50'
      text = 'text-blue-700'
      border = 'border-blue-200'
      label = 'SMTP Accepted'
      Icon = Send
      break
    case 'DELIVERY_CONFIRMED':
    case 'SENT':
      bg = 'bg-teal-50'
      text = 'text-teal-700'
      border = 'border-teal-200'
      label = 'Delivered'
      Icon = ShieldCheck
      break
    case 'ACTIVE':
      bg = 'bg-emerald-50'
      text = 'text-emerald-700'
      border = 'border-emerald-200'
      label = 'Active'
      Icon = CheckCircle2
      break
    case 'COMPLETED':
      bg = 'bg-blue-50'
      text = 'text-blue-700'
      border = 'border-blue-200'
      label = 'Completed'
      Icon = CheckCircle2
      break
    case 'READY':
      bg = 'bg-indigo-50'
      text = 'text-indigo-700'
      border = 'border-indigo-200'
      label = 'Ready'
      Icon = Send
      break
    case 'SCHEDULED':
      bg = 'bg-indigo-50'
      text = 'text-indigo-700'
      border = 'border-indigo-200'
      label = 'Scheduled'
      Icon = Clock
      break
    case 'PROCESSING':
      bg = 'bg-amber-50'
      text = 'text-amber-700'
      border = 'border-amber-200'
      label = 'Processing'
      Icon = Clock
      break
    case 'DRAFT':
      bg = 'bg-slate-100'
      text = 'text-slate-600'
      border = 'border-slate-200'
      label = 'Draft'
      Icon = Clock
      break
    case 'RETRY_PENDING':
      bg = 'bg-amber-50'
      text = 'text-amber-700'
      border = 'border-amber-200'
      label = 'Retry Pending'
      Icon = Clock
      break
    case 'FAILED':
      bg = 'bg-rose-50'
      text = 'text-rose-700'
      border = 'border-rose-200'
      label = 'Failed'
      Icon = XCircle
      break
    case 'DELIVERY_UNCERTAIN':
      bg = 'bg-purple-50'
      text = 'text-purple-700'
      border = 'border-purple-200'
      label = 'Uncertain'
      Icon = AlertTriangle
      break
    case 'SKIPPED_INACTIVE':
    case 'INACTIVE':
    case 'TERMINATED':
    case 'ON LEAVE':
      bg = 'bg-slate-100'
      text = 'text-slate-600'
      border = 'border-slate-200'
      label = status || 'Inactive'
      Icon = UserX
      break
    default:
      label = status
      break
  }

  const sizeClasses = size === 'sm'
    ? 'text-xs px-2 py-0.5 gap-1'
    : 'text-xs font-semibold px-2.5 py-1 gap-1.5'

  return (
    <span
      className={`inline-flex items-center rounded-full border ${bg} ${text} ${border} ${sizeClasses} transition-colors whitespace-nowrap`}
    >
      {showIcon && <Icon className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />}
      <span>{label}</span>
    </span>
  )
}
