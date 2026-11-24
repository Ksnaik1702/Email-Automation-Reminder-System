'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import AppLayout from '../components/AppLayout'
import KPICard from '../components/KPICard'
import StatusBadge from '../components/StatusBadge'
import Button from '../components/Button'
import {
  Send,
  Sparkles,
  Play,
  RotateCw,
  PlusCircle,
  FileCheck2,
  Clock,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Database,
  ArrowRight,
  Layers,
  Users,
  ShieldAlert,
  Server,
  Zap,
  Radio,
  FileText
} from 'lucide-react'

export default function OverviewDashboardPage() {
  const [statusMessage, setStatusMessage] = useState<string>('')
  const [statusType, setStatusType] = useState<'info' | 'success' | 'error'>('info')
  const [loading, setLoading] = useState<boolean>(false)
  const [contacts, setContacts] = useState<any[]>([])
  const [reminders, setReminders] = useState<any[]>([])
  const [recentLogs, setRecentLogs] = useState<any[]>([])
  const [trends, setTrends] = useState<any[]>([])
  const [kpis, setKpis] = useState<{
    total_executions: number
    simulated_emails: number
    smtp_accepted: number
    delivery_confirmed: number
    failed_emails: number
    retry_pending: number
  }>({
    total_executions: 0,
    simulated_emails: 0,
    smtp_accepted: 0,
    delivery_confirmed: 0,
    failed_emails: 0,
    retry_pending: 0,
  })

  // Dispatch Controls state
  const [dispatchMode, setDispatchMode] = useState<'SIMULATION' | 'LIVE_SMTP'>('SIMULATION')
  const [confirmLive, setConfirmLive] = useState<boolean>(false)
  const [triggerLoading, setTriggerLoading] = useState<boolean>(false)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

  useEffect(() => {
    fetchDashboardData()
  }, [])

  async function fetchDashboardData() {
    setLoading(true)
    try {
      // 1. Fetch contacts & reminders
      const [cRes, rRes, kpiRes, logsRes, trendsRes] = await Promise.all([
        fetch(`${API_URL}/contacts`).catch(() => null),
        fetch(`${API_URL}/reminders`).catch(() => null),
        fetch(`${API_URL}/api/analytics/kpis`).catch(() => null),
        fetch(`${API_URL}/api/analytics/recent-activity?page=1&page_size=5`).catch(() => null),
        fetch(`${API_URL}/api/analytics/trends`).catch(() => null)
      ])

      if (cRes && cRes.ok) setContacts(await cRes.json())
      if (rRes && rRes.ok) setReminders(await rRes.json())
      if (kpiRes && kpiRes.ok) {
        const kData = await kpiRes.json()
        setKpis({
          total_executions: kData.total_executions || 0,
          simulated_emails: kData.simulated_emails || 0,
          smtp_accepted: kData.smtp_accepted || 0,
          delivery_confirmed: kData.delivery_confirmed || 0,
          failed_emails: kData.failed_emails || 0,
          retry_pending: kData.retry_pending || 0,
        })
      }
      if (logsRes && logsRes.ok) {
        const lData = await logsRes.json()
        setRecentLogs(lData.items || [])
      }
      if (trendsRes && trendsRes.ok) {
        const tData = await trendsRes.json()
        setTrends(tData || [])
      }
    } catch (e) {
      console.warn('API error fetching dashboard metrics:', e)
    } finally {
      setLoading(false)
    }
  }

  // Trigger Scheduler Engine Sweep
  async function triggerSchedulerSweep() {
    setTriggerLoading(true)
    setStatusMessage('Evaluating due campaigns and reminders with scheduling engine...')
    setStatusType('info')

    try {
      const isSim = dispatchMode === 'SIMULATION'
      const queryParams = new URLSearchParams({
        simulation: String(isSim),
        confirm_live: String(confirmLive),
      })

      const res = await fetch(`${API_URL}/api/scheduler/trigger?${queryParams.toString()}`, {
        method: 'POST',
      })
      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Failed to trigger scheduler sweep')
      }

      setStatusType('success')
      setStatusMessage(
        `Scheduler cycle completed in ${data.execution_mode} mode. Processed: ${
          data.result?.campaigns_processed || 0
        } campaigns, ${data.result?.reminders_processed || 0} reminders.`
      )
      fetchDashboardData()
    } catch (err: any) {
      setStatusType('error')
      setStatusMessage(`Error: ${err.message}`)
    } finally {
      setTriggerLoading(false)
    }
  }

  // Trigger CSV Batch
  async function triggerBatch() {
    setTriggerLoading(true)
    setStatusMessage('Dispatching immediate batch cycle...')
    setStatusType('info')
    try {
      const isDry = dispatchMode === 'SIMULATION'
      const res = await fetch(`${API_URL}/dispatch-batch?dry_run=${isDry}`, {
        method: 'POST',
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || 'Batch dispatch failed')
      }
      setStatusType('success')
      setStatusMessage(
        `Batch cycle completed: ${data.processed} notification jobs evaluated in ${
          data.dry_run ? 'Dry-Run Simulation' : 'Live SMTP'
        } mode.`
      )
      fetchDashboardData()
    } catch (err: any) {
      setStatusType('error')
      setStatusMessage(`Dispatch error: ${err.message}`)
    } finally {
      setTriggerLoading(false)
    }
  }

  // Create Demo Pipeline
  async function createDemoPipeline() {
    setLoading(true)
    setStatusMessage('Provisioning complete demo pipeline records...')
    setStatusType('info')
    try {
      // 1. Create Contact
      const c = await fetch(`${API_URL}/contacts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Student Trainee',
          email: 'trainee@example.com',
          timezone: 'Asia/Kolkata',
        }),
      }).then((r) => r.json())

      // 2. Create Template
      const t = await fetch(`${API_URL}/templates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Sprint Reminder',
          subject: 'Action Required: {{name}} - Project Milestone Sync',
          body_md:
            'Hello **{{name}}**,\n\nYour milestone review is scheduled for today.\n\nBest regards,\n**Engineering Operations**',
        }),
      }).then((r) => r.json())

      // 3. Create Campaign
      const camp = await fetch(`${API_URL}/campaigns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Sprint Q4 Review',
          template_id: t.id,
          sender_name: 'Lead Instructor',
          sender_email: 'instructor@demo.com',
        }),
      }).then((r) => r.json())

      // 4. Schedule Reminder
      const fireTime = new Date(Date.now() + 60 * 1000).toISOString()
      await fetch(`${API_URL}/reminders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: 'Milestone Review Check-in',
          contact_id: c.id,
          campaign_id: camp.id,
          start_at_utc: fireTime,
          rrule: 'FREQ=DAILY;INTERVAL=1',
        }),
      })

      setStatusType('success')
      setStatusMessage('Demo pipeline created: Contact, Template, Campaign, and Daily Reminder registered!')
      fetchDashboardData()
    } catch (err: any) {
      setStatusType('error')
      setStatusMessage(`Error provisioning demo records: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const successfulTotal = kpis.simulated_emails + kpis.smtp_accepted + kpis.delivery_confirmed

  return (
    <AppLayout
      title="Operational Overview & Dispatch"
      subtitle="Enterprise notification engine, schedule orchestrator, and real-time delivery telemetry"
      isLiveMode={dispatchMode === 'LIVE_SMTP'}
      actions={
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            icon={RotateCw}
            loading={loading}
            onClick={fetchDashboardData}
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            size="sm"
            icon={PlusCircle}
            onClick={createDemoPipeline}
            disabled={loading}
          >
            Create Demo Pipeline
          </Button>
        </div>
      }
    >
      {/* Status Notice Banner */}
      {statusMessage && (
        <div
          className={`flex items-start gap-3 p-4 mb-6 rounded-xl border text-sm transition-all animate-in fade-in ${
            statusType === 'success'
              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
              : statusType === 'error'
              ? 'bg-rose-50 text-rose-800 border-rose-200'
              : 'bg-blue-50 text-blue-800 border-blue-200'
          }`}
        >
          {statusType === 'success' ? (
            <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-600 mt-0.5" />
          ) : statusType === 'error' ? (
            <XCircle className="w-5 h-5 flex-shrink-0 text-rose-600 mt-0.5" />
          ) : (
            <Sparkles className="w-5 h-5 flex-shrink-0 text-blue-600 mt-0.5" />
          )}
          <div className="flex-1 font-medium">{statusMessage}</div>
          <button
            onClick={() => setStatusMessage('')}
            className="text-xs opacity-60 hover:opacity-100 font-semibold uppercase"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* 4 Primary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KPICard
          title="Total Executions"
          value={kpis.total_executions}
          icon={Send}
          accent="indigo"
          subtitle="All recorded delivery occurrences"
          loading={loading}
        />
        <KPICard
          title="Successful / Simulated"
          value={successfulTotal}
          icon={CheckCircle2}
          accent="emerald"
          badge={kpis.total_executions > 0 ? `${Math.round((successfulTotal / kpis.total_executions) * 100)}%` : '0%'}
          badgeType="success"
          subtitle={`${kpis.simulated_emails} simulated, ${kpis.smtp_accepted} SMTP`}
          loading={loading}
        />
        <KPICard
          title="Pending Due Jobs"
          value={reminders.length + kpis.retry_pending}
          icon={Clock}
          accent="amber"
          subtitle={`${reminders.length} scheduled, ${kpis.retry_pending} in retry`}
          loading={loading}
        />
        <KPICard
          title="Failed Executions"
          value={kpis.failed_emails}
          icon={XCircle}
          accent="rose"
          badge={kpis.failed_emails > 0 ? 'Action Required' : 'Zero Failures'}
          badgeType={kpis.failed_emails > 0 ? 'warning' : 'success'}
          subtitle="Terminal transmission failures"
          loading={loading}
        />
      </div>

      {/* Dispatch Controls & Mode Selector Section */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs mb-8">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Zap className="w-5 h-5 text-indigo-600" />
              Automated Notification Dispatch Console
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Select execution environment, trigger instant worker evaluation sweeps, or execute batch test cycles.
            </p>
          </div>

          {/* Mode Switcher Radio Group */}
          <div className="flex items-center gap-2 p-1 bg-slate-100 rounded-lg border border-slate-200 self-start lg:self-auto">
            <button
              onClick={() => {
                setDispatchMode('SIMULATION')
                setConfirmLive(false)
              }}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                dispatchMode === 'SIMULATION'
                  ? 'bg-white text-emerald-700 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
              Virtual Simulation (Dry-Run)
            </button>
            <button
              onClick={() => setDispatchMode('LIVE_SMTP')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                dispatchMode === 'LIVE_SMTP'
                  ? 'bg-white text-rose-700 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Radio className="w-3.5 h-3.5 text-rose-600" />
              Live SMTP Delivery
            </button>
          </div>
        </div>

        {/* Live Mode Safety Warning */}
        {dispatchMode === 'LIVE_SMTP' && (
          <div className="mt-4 p-4 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-900 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Live Email Transmission Mode:</span> Real emails will be dispatched
                through your configured SMTP provider (e.g. Gmail / SendGrid).
                <div className="text-rose-700 mt-0.5">
                  Fail-closed safety policy strictly requires confirmation before sending.
                </div>
              </div>
            </div>
            <label className="flex items-center gap-2 font-semibold text-rose-950 cursor-pointer self-start sm:self-auto whitespace-nowrap bg-white px-3 py-1.5 rounded-md border border-rose-300 shadow-xs">
              <input
                type="checkbox"
                checked={confirmLive}
                onChange={(e) => setConfirmLive(e.target.checked)}
                className="rounded text-rose-600 focus:ring-rose-500 w-4 h-4"
              />
              Confirm Live Delivery
            </label>
          </div>
        )}

        {/* Action Buttons */}
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Button
            variant={dispatchMode === 'LIVE_SMTP' ? 'danger' : 'primary'}
            icon={Play}
            loading={triggerLoading}
            onClick={triggerSchedulerSweep}
          >
            Trigger Scheduling Engine Sweep
          </Button>

          <Button
            variant="secondary"
            icon={RotateCw}
            loading={triggerLoading}
            onClick={triggerBatch}
          >
            Trigger Batch Dispatch Cycle
          </Button>

          <Link href="/analytics">
            <Button variant="ghost" icon={ArrowRight} iconPosition="right">
              View Complete Telemetry
            </Button>
          </Link>
        </div>
      </div>

      {/* Two Column Section: Quick Pipeline Directory & Recent Execution Audit */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Left: Registered Contacts & Reminders */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-indigo-600" />
                <h3 className="text-sm font-bold text-slate-900">
                  Registered Contacts ({contacts.length})
                </h3>
              </div>
              <Link
                href="/employees"
                className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
              >
                Directory <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            {contacts.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-400">
                No contacts registered in SQLite database. Click "Create Demo Pipeline" above.
              </div>
            ) : (
              <ul className="divide-y divide-slate-100 text-xs">
                {contacts.slice(0, 5).map((c) => (
                  <li key={c.id} className="py-2.5 flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-slate-900">{c.name}</span>
                      <span className="text-slate-400 ml-1.5 font-mono">{c.email}</span>
                    </div>
                    <span className="text-[11px] text-slate-500 font-mono bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
                      {c.timezone || 'UTC'}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Database: Single Source of Truth (SQLite WAL)</span>
            <Link href="/employees" className="font-semibold text-indigo-600 hover:underline">
              Manage All Employees &rarr;
            </Link>
          </div>
        </div>

        {/* Right: Scheduled Reminders Preview */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-indigo-600" />
                <h3 className="text-sm font-bold text-slate-900">
                  Active Reminder Jobs ({reminders.length})
                </h3>
              </div>
              <Link
                href="/reminders"
                className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
              >
                Reminders <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            {reminders.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-400">
                No active reminder jobs in database. Click "Create Demo Pipeline" to seed one.
              </div>
            ) : (
              <ul className="divide-y divide-slate-100 text-xs">
                {reminders.slice(0, 5).map((r) => (
                  <li key={r.id} className="py-2.5 flex items-center justify-between">
                    <div className="min-w-0 pr-2">
                      <p className="font-semibold text-slate-900 truncate">{r.title}</p>
                      <p className="text-[11px] text-slate-400">
                        {r.rrule ? `Recurring (${r.rrule})` : 'One-time notification'}
                      </p>
                    </div>
                    <StatusBadge status={r.active ? 'ACTIVE' : 'COMPLETED'} size="sm" />
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Orchestration: APScheduler Background Worker</span>
            <Link href="/reminders" className="font-semibold text-indigo-600 hover:underline">
              View Schedules &rarr;
            </Link>
          </div>
        </div>
      </div>

      {/* Recent Execution Activity Feed */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Recent Execution Activity</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Live audit telemetry logged into the unified SQLite MessageLog repository
            </p>
          </div>
          <Link
            href="/logs"
            className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
          >
            Full Audit Logs <ArrowRight className="w-3 h-3" />
          </Link>
        </div>

        {recentLogs.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-400">
            No execution logs yet. Trigger a batch or scheduler sweep to generate logs.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 uppercase font-semibold">
                <tr>
                  <th className="py-2.5 px-3">Executed (UTC)</th>
                  <th className="py-2.5 px-3">Recipient</th>
                  <th className="py-2.5 px-3">Subject</th>
                  <th className="py-2.5 px-3">Mode</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Idempotency Key</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {recentLogs.map((log: any) => (
                  <tr key={log.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-2.5 px-3 font-mono text-slate-600 whitespace-nowrap">
                      {log.executed_at ? log.executed_at.replace('T', ' ').substring(0, 19) : 'N/A'}
                    </td>
                    <td className="py-2.5 px-3 font-medium text-slate-900">
                      {log.recipient_email}
                    </td>
                    <td className="py-2.5 px-3 text-slate-700 max-w-xs truncate" title={log.subject}>
                      {log.subject}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="font-mono text-[10px] px-2 py-0.5 bg-slate-100 rounded text-slate-700 border border-slate-200">
                        {log.execution_mode}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <StatusBadge status={log.execution_status} size="sm" />
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-400 truncate max-w-[140px]" title={log.execution_key}>
                      {log.execution_key ? log.execution_key.substring(0, 16) + '...' : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppLayout>
  )
}
