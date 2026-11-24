'use client'

import React, { useState, useEffect } from 'react'
import Sidebar from './Sidebar'
import Header, { BreadcrumbItem } from './Header'

export interface AppLayoutProps {
  children: React.ReactNode
  title: string
  subtitle?: string
  breadcrumbs?: BreadcrumbItem[]
  actions?: React.ReactNode
  isLiveMode?: boolean
}

export default function AppLayout({
  children,
  title,
  subtitle,
  breadcrumbs = [],
  actions,
  isLiveMode = false,
}: AppLayoutProps) {
  const [collapsed, setCollapsed] = useState<boolean>(false)
  const [mobileOpen, setMobileOpen] = useState<boolean>(false)

  // Persist sidebar collapsed preference in localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem('sidebar_collapsed')
      if (saved !== null) {
        setCollapsed(saved === 'true')
      }
    } catch (e) {
      // LocalStorage not available or blocked
    }
  }, [])

  const handleToggleCollapse = () => {
    setCollapsed((prev) => {
      const next = !prev
      try {
        localStorage.setItem('sidebar_collapsed', String(next))
      } catch (e) {}
      return next
    })
  }

  return (
    <div className="min-h-screen bg-[#F5F7FB] text-[#1E293B]">
      {/* Sidebar */}
      <Sidebar
        collapsed={collapsed}
        onToggleCollapse={handleToggleCollapse}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />

      {/* Main Content Area */}
      <div
        className={`flex flex-col min-h-screen transition-all duration-300 ease-in-out ${
          collapsed ? 'lg:pl-20' : 'lg:pl-64'
        }`}
      >
        {/* Top Header */}
        <Header
          title={title}
          subtitle={subtitle}
          breadcrumbs={breadcrumbs}
          actions={actions}
          onOpenMobileNav={() => setMobileOpen(true)}
          isLiveMode={isLiveMode}
        />

        {/* Content Canvas */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  )
}
