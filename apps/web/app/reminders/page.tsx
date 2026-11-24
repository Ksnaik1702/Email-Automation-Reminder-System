'use client'

import React, { useState, useEffect } from 'react'
import AppLayout from '@/components/AppLayout'
import KPICard from '@/components/KPICard'
import StatusBadge from '@/components/StatusBadge'
import SearchInput from '@/components/SearchInput'
import Button from '@/components/Button'
import EmptyState from '@/components/EmptyState'
import Drawer from '@/components/Drawer'
import {
  Clock,
  CheckCircle2,
  Calendar,
  AlertCircle,
  Play,
  RotateCcw,
  User,
  Filter,
  Layers,
  ArrowUpDown,
  RefreshCw
} from 'lucide-react'

interface ReminderJob {
  id: number
  campaign_id?: number | null
  campaign_name?: string | null
  employee_id: number
  employee_name: string
  employee_email: string
  employee_code: string
  reminder_title: string
  scheduled_at: string
  timezone: string
  recurrence_type: string
  status: string
  last_executed_at?: string | null
  created_at: string
}

export default function RemindersPage() {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

  const [reminders, setReminders] = useState<ReminderJob[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('All')
  const [recurrenceFilter, setRecurrenceFilter] = useState<string>('All')
  const [selectedReminder, setSelectedReminder] = useState<ReminderJob | null>(null)
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false)
  const [isSweeping, setIsSweeping] = useState<boolean>(false)
  const [sweepMessage, setSweepMessage] = useState<string>('')

  useEffect(() => {
    fetchReminders()
  }, [statusFilter])

  async function fetchReminders() {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (statusFilter !== 'All') params.append('status', statusFilter)
      if (searchTerm.trim()) params.append('search', searchTerm.trim())

      const res = await fetch(`${API_URL}/api/scheduler/reminders?${params.toString()}`)
      if (res.ok) {
        const data = await res.json()
        setReminders(data.items || [])
      } else {
        console.error('Failed to fetch reminders')
      }
    } catch (e) {
      console.error('API connection error:', e)
    } finally {
      setLoading(false)
    }
  }

  async function handleTriggerSweep() {
    setIsSweeping(true)
    setSweepMessage('')
    try {
      const res = await fetch(`${API_URL}/api/scheduler/trigger?simulation=true`, {
        method: 'POST'
      })
      if (res.ok) {
        const data = await res.json()
        const r = data.result || {}
        setSweepMessage(`Engine sweep complete! Processed ${r.reminders_processed || 0} reminders, ${r.campaigns_processed || 0} campaigns.`)
        fetchReminders()
      } else {
        const err = await res.json()
        setSweepMessage(`Sweep failed: ${err.detail || 'Server error'}`)
      }
    } catch (e: any) {
      setSweepMessage(`Sweep error: ${e.message}`)
    } finally {
      setIsSweeping(false)
    }
  }

  const filteredReminders = reminders.filter((r) => {
    if (recurrenceFilter !== 'All' && r.recurrence_type.toLowerCase() !== recurrenceFilter.toLowerCase()) {
      return false
    }
    if (searchTerm.trim()) {
      const s = searchTerm.toLowerCase()
      const match =
        r.reminder_title.toLowerCase().includes(s) ||
        r.employee_name.toLowerCase().includes(s) ||
        r.employee_email.toLowerCase().includes(s) ||
        r.employee_code.toLowerCase().includes(s)
      if (!match) return false
    }
    return true
  })

  const totalCount = reminders.length
  const activeCount = reminders.filter((r) => r.status.toLowerCase() === 'active').length
  const completedCount = reminders.filter((r) => r.status.toLowerCase() === 'completed').length
  const recurringCount = reminders.filter((r) => r.recurrence_type && r.recurrence_type !== 'None').length

  function formatDateTime(dtStr?: string | null) {
    if (!dtStr) return '—'
    try {
      const d = new Date(dtStr)
      return d.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short'
      })
    } catch {
      return dtStr
    }
  }

  return (
    <AppLayout
      title="Scheduled Reminders"
      subtitle="Automated trigger schedules, recurring cron jobs, and worker execution queue"
      actions={
        <Button
          variant="primary"
          icon={<Play className="w-4 h-4" />}
          loading={isSweeping}
          onClick={handleTriggerSweep}
        >
          Run Engine Sweep
        </Button>
      }
    >
      {sweepMessage && (
        <div className="mb-6 p-4 rounded-xl bg-teal-50 border border-teal-200 text-teal-800 text-sm flex items-center justify-between shadow-sm animate-fade-in">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-5 h-5 text-teal-600 flex-shrink-0" />
            <span className="font-medium">{sweepMessage}</span>
          </div>
          <button
            onClick={() => setSweepMessage('')}
            className="text-teal-600 hover:text-teal-800 font-semibold text-xs ml-4"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
        <KPICard
          title="Total Reminder Jobs"
          value={totalCount}
          icon={Calendar}
          trendText="All database records"
          trendUp={true}
          accentColor="indigo"
          loading={loading}
        />
        <KPICard
          title="Active Schedules"
          value={activeCount}
          icon={Clock}
          trendText="Awaiting trigger dispatch"
          trendUp={true}
          accentColor="teal"
          loading={loading}
        />
        <KPICard
          title="Completed Jobs"
          value={completedCount}
          icon={CheckCircle2}
          trendText="Finished execution cycles"
          trendUp={true}
          accentColor="green"
          loading={loading}
        />
        <KPICard
          title="Recurring Jobs"
          value={recurringCount}
          icon={RotateCcw}
          trendText="Daily, Weekly, Monthly cycles"
          trendUp={true}
          accentColor="purple"
          loading={loading}
        />
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white border border-slate-200/80 rounded-2xl p-5 mb-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex-1 max-w-md">
            <SearchInput
              value={searchTerm}
              onChange={(e: any) => setSearchTerm(typeof e === 'string' ? e : e.target.value)}
              onClear={() => setSearchTerm('')}
              placeholder="Search reminder title, recipient name, or email..."
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center space-x-2">
              <Filter className="w-4 h-4 text-slate-400" />
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Status:
              </label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                aria-label="Filter reminders by status"
                className="bg-slate-50 border border-slate-200 text-slate-700 text-sm rounded-lg px-3 py-2 font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="All">All Statuses</option>
                <option value="Active">Active</option>
                <option value="Completed">Completed</option>
                <option value="Paused">Paused</option>
                <option value="Cancelled">Cancelled</option>
              </select>
            </div>

            <div className="flex items-center space-x-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Recurrence:
              </label>
              <select
                value={recurrenceFilter}
                onChange={(e) => setRecurrenceFilter(e.target.value)}
                aria-label="Filter reminders by recurrence"
                className="bg-slate-50 border border-slate-200 text-slate-700 text-sm rounded-lg px-3 py-2 font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="All">All Frequencies</option>
                <option value="None">One-Off (None)</option>
                <option value="Daily">Daily</option>
                <option value="Weekly">Weekly</option>
                <option value="Monthly">Monthly</option>
              </select>
            </div>

            <Button
              variant="outline"
              size="sm"
              icon={<RefreshCw className="w-3.5 h-3.5" />}
              onClick={fetchReminders}
            >
              Refresh
            </Button>
          </div>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-white border border-slate-200/80 rounded-2xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/75 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3.5 px-5">ID</th>
                <th className="py-3.5 px-5">Reminder Title</th>
                <th className="py-3.5 px-5">Target Recipient</th>
                <th className="py-3.5 px-5">Scheduled For</th>
                <th className="py-3.5 px-5">Recurrence</th>
                <th className="py-3.5 px-5">Timezone</th>
                <th className="py-3.5 px-5">Status</th>
                <th className="py-3.5 px-5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm text-slate-700">
              {filteredReminders.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12">
                    <EmptyState
                      icon={Clock}
                      title="No scheduled reminders found"
                      description={
                        searchTerm || statusFilter !== 'All'
                          ? 'No reminder jobs match your search or filter settings.'
                          : 'No automated reminder jobs are currently registered in the database.'
                      }
                      actionLabel={searchTerm || statusFilter !== 'All' ? 'Reset Filters' : undefined}
                      onAction={() => {
                        setSearchTerm('')
                        setStatusFilter('All')
                        setRecurrenceFilter('All')
                      }}
                    />
                  </td>
                </tr>
              ) : (
                filteredReminders.map((job) => (
                  <tr
                    key={job.id}
                    onClick={() => {
                      setSelectedReminder(job)
                      setIsDrawerOpen(true)
                    }}
                    className="hover:bg-indigo-50/30 transition-colors cursor-pointer group"
                  >
                    <td className="py-3.5 px-5 font-mono text-xs text-slate-400">
                      #{job.id}
                    </td>
                    <td className="py-3.5 px-5 font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors">
                      {job.reminder_title}
                      {job.campaign_name && (
                        <span className="block text-xs font-normal text-slate-400">
                          Linked: {job.campaign_name}
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-5">
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs flex-shrink-0">
                          {job.employee_name ? job.employee_name.charAt(0) : 'U'}
                        </div>
                        <div>
                          <p className="font-medium text-slate-900 leading-tight">
                            {job.employee_name || 'Unassigned'}
                          </p>
                          <p className="text-xs text-slate-400 leading-tight">
                            {job.employee_email}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-5 font-mono text-xs text-slate-600">
                      {formatDateTime(job.scheduled_at)}
                    </td>
                    <td className="py-3.5 px-5">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
                        {job.recurrence_type || 'None'}
                      </span>
                    </td>
                    <td className="py-3.5 px-5 text-xs text-slate-500 font-mono">
                      {job.timezone}
                    </td>
                    <td className="py-3.5 px-5">
                      <StatusBadge status={job.status} />
                    </td>
                    <td className="py-3.5 px-5 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedReminder(job)
                          setIsDrawerOpen(true)
                        }}
                      >
                        Details
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Reminder Details Drawer */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={selectedReminder ? selectedReminder.reminder_title : 'Reminder Details'}
        subtitle={selectedReminder ? `Job #${selectedReminder.id} Specifications` : ''}
        size="md"
      >
        {selectedReminder && (
          <div className="space-y-6">
            <div className="bg-slate-50 rounded-xl p-4 border border-slate-200/70">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Execution Status
              </h4>
              <div className="flex items-center justify-between">
                <StatusBadge status={selectedReminder.status} />
                <span className="text-xs text-slate-500 font-mono">
                  Job ID: {selectedReminder.id}
                </span>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                Recipient Details
              </h4>
              <div className="p-4 rounded-xl border border-slate-200 bg-white space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Employee Name:</span>
                  <span className="font-semibold text-slate-900">{selectedReminder.employee_name}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Email Address:</span>
                  <span className="font-mono text-slate-800">{selectedReminder.employee_email}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Employee Code:</span>
                  <span className="font-mono text-slate-800">{selectedReminder.employee_code}</span>
                </div>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                Timing & Recurrence
              </h4>
              <div className="p-4 rounded-xl border border-slate-200 bg-white space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Scheduled At (UTC):</span>
                  <span className="font-mono text-slate-800">{formatDateTime(selectedReminder.scheduled_at)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Timezone:</span>
                  <span className="font-mono text-slate-800">{selectedReminder.timezone}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Recurrence Frequency:</span>
                  <span className="font-semibold text-indigo-600">{selectedReminder.recurrence_type || 'None'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Last Executed:</span>
                  <span className="font-mono text-slate-800">{formatDateTime(selectedReminder.last_executed_at)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Created At:</span>
                  <span className="font-mono text-slate-800">{formatDateTime(selectedReminder.created_at)}</span>
                </div>
              </div>
            </div>

            {selectedReminder.campaign_name && (
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                  Linked Campaign
                </h4>
                <div className="p-4 rounded-xl border border-slate-200 bg-indigo-50/50">
                  <p className="font-semibold text-indigo-900">{selectedReminder.campaign_name}</p>
                  <p className="text-xs text-indigo-600 mt-1">Campaign ID: #{selectedReminder.campaign_id}</p>
                </div>
              </div>
            )}
          </div>
        )}
      </Drawer>
    </AppLayout>
  )
}
