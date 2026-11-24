'use client'

import React from 'react'
import Link from 'next/link'
import {
  Menu,
  ChevronRight,
  ShieldCheck,
  Radio,
  Sparkles,
  Server,
  RefreshCw
} from 'lucide-react'

export interface BreadcrumbItem {
  label: string
  href?: string
}

export interface HeaderProps {
  title: string
  subtitle?: string
  breadcrumbs?: BreadcrumbItem[]
  actions?: React.ReactNode
  onOpenMobileNav: () => void
  isLiveMode?: boolean
}

export default function Header({
  title,
  subtitle,
  breadcrumbs = [],
  actions,
  onOpenMobileNav,
  isLiveMode = false,
}: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 flex items-center justify-between min-h-[64px] px-4 sm:px-6 bg-white border-b border-slate-200 shadow-sm transition-all">
      {/* Left: Mobile trigger & Breadcrumbs / Title */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onOpenMobileNav}
          aria-label="Open navigation menu"
          className="flex lg:hidden p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex flex-col min-w-0">
          {breadcrumbs.length > 0 && (
            <nav className="flex items-center gap-1.5 text-xs text-slate-500 mb-0.5 overflow-hidden">
              <Link href="/" className="hover:text-indigo-600 transition-colors truncate">
                Hub
              </Link>
              {breadcrumbs.map((crumb, idx) => (
                <React.Fragment key={idx}>
                  <ChevronRight className="w-3 h-3 text-slate-400 flex-shrink-0" />
                  {crumb.href ? (
                    <Link
                      href={crumb.href}
                      className="hover:text-indigo-600 transition-colors truncate"
                    >
                      {crumb.label}
                    </Link>
                  ) : (
                    <span className="text-slate-700 font-medium truncate">
                      {crumb.label}
                    </span>
                  )}
                </React.Fragment>
              ))}
            </nav>
          )}

          <h1 className="text-lg sm:text-xl font-bold tracking-tight text-slate-900 leading-tight truncate">
            {title}
          </h1>
          {subtitle && (
            <p className="hidden md:block text-xs text-slate-500 truncate mt-0.5">
              {subtitle}
            </p>
          )}
        </div>
      </div>

      {/* Right: Environment Indicator Badge & Actions */}
      <div className="flex items-center gap-3">
        {/* Environment Status Pill */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-semibold shadow-xs">
          {isLiveMode ? (
            <div className="flex items-center gap-1.5 text-rose-700 bg-rose-50 border-rose-200">
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span>
              <span>Live SMTP Active</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-emerald-800 bg-emerald-50 border-emerald-200 px-3 py-1 rounded-full border">
              <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
              <span>Simulation (Dry-Run)</span>
            </div>
          )}
        </div>

        {/* Action Slot */}
        {actions && (
          <div className="flex items-center gap-2">{actions}</div>
        )}
      </div>
    </header>
  )
}
