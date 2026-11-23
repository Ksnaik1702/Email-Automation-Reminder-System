'use client'

import React, { useState, useEffect } from 'react'

export default function Home() {
  const [status, setStatus] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(false)
  const [contacts, setContacts] = useState<any[]>([])
  const [reminders, setReminders] = useState<any[]>([])

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

  useEffect(() => {
    fetchData()
  }, [])

  async function fetchData() {
    try {
      const cRes = await fetch(`${API_URL}/contacts`)
      if (cRes.ok) setContacts(await cRes.json())
      const rRes = await fetch(`${API_URL}/reminders`)
      if (rRes.ok) setReminders(await rRes.json())
    } catch (e) {
      console.warn('API is not running yet or unreachable:', e)
    }
  }

  async function createDemoPipeline() {
    setLoading(true)
    setStatus('Creating demo pipeline records...')
    try {
      // 1. Create Contact
      const c = await fetch(`${API_URL}/contacts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Student Trainee',
          email: 'trainee@example.com',
          timezone: 'Asia/Kolkata'
        })
      }).then(r => r.json())

      // 2. Create Template
      const t = await fetch(`${API_URL}/templates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Sprint Reminder',
          subject: 'Action Required: {{name}} - Project Milestone Sync',
          body_md: 'Hello **{{name}}**,\n\nYour milestone review is scheduled for today.\n\nBest regards,\n**Engineering Operations**'
        })
      }).then(r => r.json())

      // 3. Create Campaign
      const camp = await fetch(`${API_URL}/campaigns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Sprint Q4 Review',
          template_id: t.id,
          sender_name: 'Lead Instructor',
          sender_email: 'instructor@demo.com'
        })
      }).then(r => r.json())

      // 4. Schedule Reminder (due 1 minute from now)
      const fireTime = new Date(Date.now() + 60 * 1000).toISOString()
      await fetch(`${API_URL}/reminders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: 'Milestone Review Check-in',
          contact_id: c.id,
          campaign_id: camp.id,
          start_at_utc: fireTime,
          rrule: 'FREQ=DAILY;INTERVAL=1'
        })
      })

      setStatus('✅ Success: Contact, Template, Campaign, and Daily Reminder created in SQLite DB!')
      fetchData()
    } catch (err: any) {
      setStatus(`❌ Error connecting to API: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  async function triggerBatch() {
    try {
      setStatus('Dispatching batch...')
      const res = await fetch(`${API_URL}/dispatch-batch?dry_run=true`, { method: 'POST' })
      const data = await res.json()
      setStatus(`🚀 Batch cycle completed: ${data.processed} notification jobs evaluated in dry-run mode.`)
      fetchData()
    } catch (err: any) {
      setStatus(`❌ Dispatch error: ${err.message}`)
    }
  }

  return (
    <main style={{ maxWidth: 880, margin: '40px auto', padding: '0 20px' }}>
      <header style={{ marginBottom: 32, paddingBottom: 16, borderBottom: '1px solid #e2e8f0' }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, margin: 0, color: '#0f172a' }}>
          📧 Email Automation &amp; Reminder Hub
        </h1>
        <p style={{ color: '#64748b', marginTop: 6, fontSize: 14 }}>
          Control plane for recipient contacts, dynamic message templates, RRULE recurring schedules, and send metrics.
        </p>
      </header>

      {/* Action Controls */}
      <section style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
        <a
          href="/employees"
          style={{
            backgroundColor: '#0f172a',
            color: '#fff',
            textDecoration: 'none',
            borderRadius: 6,
            padding: '10px 18px',
            fontSize: 14,
            fontWeight: 600,
            display: 'inline-flex',
            alignItems: 'center'
          }}
        >
          Workforce Directory
        </a>

        <a
          href="/templates"
          style={{
            backgroundColor: '#2563eb',
            color: '#fff',
            textDecoration: 'none',
            borderRadius: 6,
            padding: '10px 18px',
            fontSize: 14,
            fontWeight: 600,
            display: 'inline-flex',
            alignItems: 'center'
          }}
        >
          Email Templates Studio
        </a>

        <a
          href="/campaigns"
          style={{
            backgroundColor: '#059669',
            color: '#fff',
            textDecoration: 'none',
            borderRadius: 6,
            padding: '10px 18px',
            fontSize: 14,
            fontWeight: 600,
            display: 'inline-flex',
            alignItems: 'center'
          }}
        >
          Email Campaigns Studio
        </a>

        <button
          onClick={createDemoPipeline}
          disabled={loading}
          style={{
            backgroundColor: '#2563eb',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            padding: '10px 18px',
            fontSize: 14,
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          {loading ? 'Creating...' : '+ Create Demo Campaign & Reminder'}
        </button>

        <button
          onClick={triggerBatch}
          style={{
            backgroundColor: '#059669',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            padding: '10px 18px',
            fontSize: 14,
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          ⚡ Trigger Immediate Dispatch
        </button>
      </section>

      {/* Status Box */}
      {status && (
        <div style={{ padding: '12px 16px', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 6, marginBottom: 24, fontSize: 13, color: '#1e40af' }}>
          {status}
        </div>
      )}

      {/* Content Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* Contacts */}
        <div style={{ background: '#fff', padding: 20, borderRadius: 8, border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <h2 style={{ fontSize: 18, margin: '0 0 12px 0' }}>👥 Registered Contacts ({contacts.length})</h2>
          {contacts.length === 0 ? (
            <p style={{ fontSize: 13, color: '#94a3b8' }}>No contacts yet. Click "Create Demo Campaign" to add.</p>
          ) : (
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: 13 }}>
              {contacts.map((c) => (
                <li key={c.id} style={{ padding: '8px 0', borderBottom: '1px solid #f1f5f9' }}>
                  <strong>{c.name}</strong> &bull; <span style={{ color: '#64748b' }}>{c.email}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Reminders */}
        <div style={{ background: '#fff', padding: 20, borderRadius: 8, border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <h2 style={{ fontSize: 18, margin: '0 0 12px 0' }}>⏰ Scheduled Reminders ({reminders.length})</h2>
          {reminders.length === 0 ? (
            <p style={{ fontSize: 13, color: '#94a3b8' }}>No reminders in database yet.</p>
          ) : (
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: 13 }}>
              {reminders.map((r) => (
                <li key={r.id} style={{ padding: '8px 0', borderBottom: '1px solid #f1f5f9' }}>
                  <strong>{r.title}</strong><br />
                  <span style={{ fontSize: 11, color: '#64748b' }}>Rule: {r.rrule || 'One-off'}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </main>
  )
}
