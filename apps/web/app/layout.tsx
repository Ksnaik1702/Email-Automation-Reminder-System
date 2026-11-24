import type { Metadata } from 'next'
import React from 'react'
import './globals.css'

export const metadata: Metadata = {
  title: 'Workforce Hub & Email Automation',
  description: 'Enterprise workforce management, email automation, campaign orchestration, and delivery telemetry',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#F5F7FB] text-[#1E293B]">
        {children}
      </body>
    </html>
  )
}
