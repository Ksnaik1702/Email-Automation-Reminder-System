import type { Metadata } from 'next'
import React from 'react'

export const metadata: Metadata = {
  title: 'Email Automation & Reminder System',
  description: 'Manage contacts, campaign templates, recurring schedules, and delivery telemetry',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: 'system-ui, -apple-system, sans-serif', backgroundColor: '#f8fafc', color: '#1e293b' }}>
        {children}
      </body>
    </html>
  )
}
