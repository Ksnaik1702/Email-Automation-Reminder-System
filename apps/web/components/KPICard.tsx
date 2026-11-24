'use client'

import React from 'react'
import { LucideIcon } from 'lucide-react'

export interface KPICardProps {
  title: string
  value: string | number
  icon: LucideIcon
  subtitle?: string
  trendText?: string
  trendUp?: boolean
  accent?: 'indigo' | 'emerald' | 'amber' | 'rose' | 'teal' | 'blue' | 'purple' | 'slate' | 'green'
  accentColor?: string
  badge?: string
  badgeType?: 'success' | 'warning' | 'info' | 'neutral'
  loading?: boolean
}

const accentMap: Record<string, { iconBg: string; borderHover: string; ring: string }> = {
  indigo: {
    iconBg: 'bg-indigo-50 text-indigo-600',
    borderHover: 'hover:border-indigo-300',
    ring: 'focus-within:ring-indigo-500',
  },
  emerald: {
    iconBg: 'bg-emerald-50 text-emerald-600',
    borderHover: 'hover:border-emerald-300',
    ring: 'focus-within:ring-emerald-500',
  },
  green: {
    iconBg: 'bg-emerald-50 text-emerald-600',
    borderHover: 'hover:border-emerald-300',
    ring: 'focus-within:ring-emerald-500',
  },
  amber: {
    iconBg: 'bg-amber-50 text-amber-600',
    borderHover: 'hover:border-amber-300',
    ring: 'focus-within:ring-amber-500',
  },
  rose: {
    iconBg: 'bg-rose-50 text-rose-600',
    borderHover: 'hover:border-rose-300',
    ring: 'focus-within:ring-rose-500',
  },
  teal: {
    iconBg: 'bg-teal-50 text-teal-600',
    borderHover: 'hover:border-teal-300',
    ring: 'focus-within:ring-teal-500',
  },
  blue: {
    iconBg: 'bg-blue-50 text-blue-600',
    borderHover: 'hover:border-blue-300',
    ring: 'focus-within:ring-blue-500',
  },
  purple: {
    iconBg: 'bg-purple-50 text-purple-600',
    borderHover: 'hover:border-purple-300',
    ring: 'focus-within:ring-purple-500',
  },
  slate: {
    iconBg: 'bg-slate-100 text-slate-600',
    borderHover: 'hover:border-slate-300',
    ring: 'focus-within:ring-slate-500',
  },
}

export default function KPICard({
  title,
  value,
  icon: Icon,
  subtitle,
  trendText,
  trendUp,
  accent,
  accentColor,
  badge,
  badgeType = 'neutral',
  loading = false,
}: KPICardProps) {
  const chosenAccent = (accentColor || accent || 'indigo') as string
  const styles = accentMap[chosenAccent] || accentMap.indigo
  const displaySubtitle = subtitle || trendText

  return (
    <div
      className={`bg-white rounded-xl border border-slate-200 p-5 shadow-sm transition-all duration-200 hover:shadow-md ${styles.borderHover}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 truncate">
            {title}
          </p>
          <div className="mt-2 flex items-baseline gap-2">
            {loading ? (
              <div className="h-8 w-20 bg-slate-200 animate-pulse rounded"></div>
            ) : (
              <span className="text-2xl font-bold tracking-tight text-slate-900">
                {typeof value === 'number' ? value.toLocaleString() : value}
              </span>
            )}
            {badge && (
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  badgeType === 'success'
                    ? 'bg-emerald-50 text-emerald-700'
                    : badgeType === 'warning'
                    ? 'bg-amber-50 text-amber-700'
                    : badgeType === 'info'
                    ? 'bg-blue-50 text-blue-700'
                    : 'bg-slate-100 text-slate-600'
                }`}
              >
                {badge}
              </span>
            )}
          </div>
          {displaySubtitle && (
            <p className="mt-1 text-xs text-slate-500 truncate">{displaySubtitle}</p>
          )}
        </div>

        <div className={`p-3 rounded-lg flex-shrink-0 ${styles.iconBg}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  )
}
