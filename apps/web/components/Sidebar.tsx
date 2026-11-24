'use client'

import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  Users,
  Megaphone,
  CalendarClock,
  FileCode2,
  BarChart3,
  ScrollText,
  Sparkles,
  ShieldAlert,
  ChevronLeft,
  ChevronRight,
  MailCheck,
  Building2
} from 'lucide-react'

export interface SidebarProps {
  collapsed: boolean
  onToggleCollapse: () => void
  mobileOpen: boolean
  onCloseMobile: () => void
}

const navItems = [
  {
    name: 'Overview',
    href: '/',
    icon: LayoutDashboard,
    badge: null,
  },
  {
    name: 'Employees',
    href: '/employees',
    icon: Users,
    badge: null,
  },
  {
    name: 'Campaigns',
    href: '/campaigns',
    icon: Megaphone,
    badge: null,
  },
  {
    name: 'Scheduled Reminders',
    href: '/reminders',
    icon: CalendarClock,
    badge: null,
  },
  {
    name: 'Template Studio',
    href: '/templates',
    icon: FileCode2,
    badge: null,
  },
  {
    name: 'Analytics',
    href: '/analytics',
    icon: BarChart3,
    badge: null,
  },
  {
    name: 'Delivery Audit Logs',
    href: '/logs',
    icon: ScrollText,
    badge: null,
  },
]

export default function Sidebar({
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
}: SidebarProps) {
  const pathname = usePathname()

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/60 backdrop-blur-sm lg:hidden transition-opacity"
          onClick={onCloseMobile}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 flex flex-col bg-[#172554] text-white transition-all duration-300 ease-in-out border-r border-[#1e3a8a]/40 shadow-xl ${
          collapsed ? 'w-20' : 'w-64'
        } ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Branding / Header */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-blue-950/80 bg-[#121c42]">
          <Link href="/" className="flex items-center gap-3 overflow-hidden group">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-indigo-600 text-white shadow-md shadow-indigo-900/40 group-hover:bg-indigo-500 transition-colors flex-shrink-0">
              <MailCheck className="w-5 h-5" />
            </div>
            {!collapsed && (
              <div className="flex flex-col min-w-0">
                <span className="font-bold text-sm tracking-tight text-white leading-tight truncate">
                  Workforce Hub
                </span>
                <span className="text-[11px] font-medium text-indigo-300 tracking-wide uppercase truncate">
                  Email Automation
                </span>
              </div>
            )}
          </Link>

          {/* Desktop Collapse Toggle */}
          <button
            onClick={onToggleCollapse}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className="hidden lg:flex items-center justify-center w-7 h-7 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
          {!collapsed && (
            <p className="px-3 pb-2 text-[10px] font-semibold tracking-wider text-slate-400 uppercase">
              Core Modules
            </p>
          )}

          {navItems.map((item) => {
            const Icon = item.icon
            const isActive =
              item.href === '/'
                ? pathname === '/'
                : pathname.startsWith(item.href)

            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={onCloseMobile}
                title={collapsed ? item.name : undefined}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 group relative ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-950/30'
                    : 'text-slate-300 hover:bg-white/10 hover:text-white'
                } ${collapsed ? 'justify-center px-0' : ''}`}
              >
                <Icon
                  className={`w-5 h-5 flex-shrink-0 transition-transform duration-150 ${
                    isActive ? 'text-white' : 'text-slate-400 group-hover:text-white group-hover:scale-105'
                  }`}
                />
                {!collapsed && (
                  <span className="truncate flex-1">{item.name}</span>
                )}
                {!collapsed && item.badge && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full font-semibold bg-white/20 text-white">
                    {item.badge}
                  </span>
                )}

                {/* Collapsed Tooltip */}
                {collapsed && (
                  <div className="absolute left-full ml-3 hidden group-hover:flex items-center px-2.5 py-1.5 rounded-md bg-slate-900 text-white text-xs whitespace-nowrap shadow-lg z-50 border border-slate-800">
                    {item.name}
                  </div>
                )}
              </Link>
            )
          })}
        </nav>

        {/* System Mode Footer Badge */}
        <div className="p-3 border-t border-blue-950/80 bg-[#121c42]">
          {!collapsed ? (
            <div className="flex items-center gap-3 p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-600/30">
              <div className="relative flex items-center justify-center flex-shrink-0 w-8 h-8 rounded-full bg-emerald-900/60 text-emerald-400">
                <span className="absolute w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                <span className="relative w-2 h-2 rounded-full bg-emerald-400"></span>
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-emerald-300 truncate">
                  Simulation Mode
                </p>
                <p className="text-[11px] text-slate-400 truncate">
                  Zero-risk safe sandbox
                </p>
              </div>
            </div>
          ) : (
            <div
              title="Simulation Mode Active (Zero-Risk Safe Sandbox)"
              className="flex justify-center p-2 rounded-lg bg-emerald-950/40 border border-emerald-600/30"
            >
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
            </div>
          )}
        </div>
      </aside>
    </>
  )
}
