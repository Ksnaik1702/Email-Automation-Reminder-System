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
  FileText,
  Clock,
  Download,
  Filter,
  RefreshCw,
  Search,
  CheckCircle2,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Copy,
  Check,
  ShieldCheck,
  Hash,
  Mail,
  Layers
} from 'lucide-react'

interface ActivityLogItem {
  id: number
  recipient_email: string
  subject: string
  campaign_id?: number
  campaign_name?: string
  reminder_id?: number
  reminder_title?: string
  execution_mode: string
  execution_status: string
  attempt_count: number
  error_category?: string
  error_message?: string
  message_id?: string
  smtp_queue_id?: string
  provider_message_id?: string
  executed_at: string
}

export default function DeliveryLogsPage() {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

  const [logs, setLogs] = useState<ActivityLogItem[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [totalCount, setTotalCount] = useState<number>(0)
  const [page, setPage] = useState<number>(1)
  const [pageSize, setPageSize] = useState<number>(20)
  const [totalPages, setTotalPages] = useState<number>(1)

  // Filters
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [modeFilter, setModeFilter] = useState<string>('ALL')
  const [statusFilter, setStatusFilter] = useState<string>('ALL')
  const [startDate, setStartDate] = useState<string>('')
  const [endDate, setEndDate] = useState<string>('')

  // Drawer
  const [selectedLog, setSelectedLog] = useState<ActivityLogItem | null>(null)
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false)
  const [copiedKey, setCopiedKey] = useState<string>('')

  // Export
  const [exporting, setExporting] = useState<boolean>(false)

  useEffect(() => {
    fetchLogs()
  }, [page, pageSize, modeFilter, statusFilter, startDate, endDate])

  async function fetchLogs() {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('page', String(page))
      params.set('page_size', String(pageSize))
      if (modeFilter !== 'ALL') params.set('execution_mode', modeFilter)
      if (statusFilter !== 'ALL') params.set('status', statusFilter)
      if (startDate) params.set('start_date', startDate)
      if (endDate) params.set('end_date', endDate)
      if (searchTerm.trim()) params.set('search', searchTerm.trim())

      const res = await fetch(`${API_URL}/api/analytics/recent-activity?${params.toString()}`)
      if (res.ok) {
        const data = await res.json()
        setLogs(data.items || [])
        setTotalPages(data.total_pages || 1)
        setTotalCount(data.total_count || 0)
      } else {
        console.error('Failed to fetch audit logs')
      }
    } catch (e) {
      console.error('API error:', e)
    } finally {
      setLoading(false)
    }
  }

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault()
    setPage(1)
    fetchLogs()
  }

  async function handleExport() {
    setExporting(true)
    try {
      const params = new URLSearchParams()
      params.set('export_type', 'complete')
      if (modeFilter !== 'ALL') params.set('execution_mode', modeFilter)
      if (statusFilter !== 'ALL') params.set('status', statusFilter)
      if (startDate) params.set('start_date', startDate)
      if (endDate) params.set('end_date', endDate)
      if (searchTerm.trim()) params.set('search', searchTerm.trim())

      const res = await fetch(`${API_URL}/api/analytics/export?${params.toString()}`)
      if (res.ok) {
        const blob = await res.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `delivery_audit_log_${new Date().toISOString().slice(0, 10)}.csv`
        document.body.appendChild(a)
        a.click()
        a.remove()
        window.URL.revokeObjectURL(url)
      } else {
        alert('Failed to download CSV export.')
      }
    } catch (e: any) {
      alert(`Export error: ${e.message}`)
    } finally {
      setExporting(false)
    }
  }

  function copyToClipboard(text: string, label: string) {
    navigator.clipboard.writeText(text)
    setCopiedKey(label)
    setTimeout(() => setCopiedKey(''), 2000)
  }

  return (
    <AppLayout
      title="Delivery Audit Logs"
      subtitle="Complete chronological audit trail of all simulation dry-runs and live SMTP dispatches"
      actions={
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            icon={<RefreshCw className="w-4 h-4" />}
            onClick={fetchLogs}
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            size="sm"
            icon={<Download className="w-4 h-4" />}
            loading={exporting}
            onClick={handleExport}
          >
            Download CSV Audit Log
          </Button>
        </div>
      }
    >
      {/* Filter and Search Bar */}
      <div className="bg-white border border-slate-200/80 rounded-2xl p-5 mb-6 shadow-sm">
        <form onSubmit={handleSearchSubmit} className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex-1 max-w-md">
            <SearchInput
              value={searchTerm}
              onChange={(e: any) => setSearchTerm(typeof e === 'string' ? e : e.target.value)}
              onClear={() => {
                setSearchTerm('')
                setPage(1)
              }}
              placeholder="Search recipient email, subject, or message ID..."
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center space-x-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Mode:
              </label>
              <select
                value={modeFilter}
                onChange={(e) => {
                  setModeFilter(e.target.value)
                  setPage(1)
                }}
                aria-label="Filter logs by execution mode"
                className="bg-slate-50 border border-slate-200 text-slate-700 text-sm rounded-lg px-3 py-2 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              >
                <option value="ALL">All Modes</option>
                <option value="SIMULATION">SIMULATION (Dry-Run)</option>
                <option value="LIVE_SMTP">LIVE_SMTP</option>
              </select>
            </div>

            <div className="flex items-center space-x-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Status:
              </label>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value)
                  setPage(1)
                }}
                aria-label="Filter logs by execution status"
                className="bg-slate-50 border border-slate-200 text-slate-700 text-sm rounded-lg px-3 py-2 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              >
                <option value="ALL">All Statuses</option>
                <option value="SIMULATED_SUCCESS">SIMULATED_SUCCESS</option>
                <option value="SMTP_ACCEPTED">SMTP_ACCEPTED</option>
                <option value="DELIVERY_CONFIRMED">DELIVERY_CONFIRMED</option>
                <option value="FAILED">FAILED</option>
                <option value="RETRY_PENDING">RETRY_PENDING</option>
                <option value="DELIVERY_UNCERTAIN">DELIVERY_UNCERTAIN</option>
                <option value="SKIPPED_INACTIVE">SKIPPED_INACTIVE</option>
                <option value="SKIPPED_DUPLICATE">SKIPPED_DUPLICATE</option>
              </select>
            </div>

            <Button variant="primary" size="sm" type="submit">
              Apply Filters
            </Button>
          </div>
        </form>
      </div>

      {/* Main Audit Log Table */}
      <div className="bg-white border border-slate-200/80 rounded-2xl shadow-sm overflow-hidden">
        <div className="p-5 pb-3 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="font-bold text-slate-900 text-base">Execution Records</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Showing {logs.length} of {totalCount} total logged actions
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-xs text-slate-500">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="bg-slate-50/75 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-5">Timestamp (UTC)</th>
                <th className="py-3 px-5">Recipient</th>
                <th className="py-3 px-5">Subject</th>
                <th className="py-3 px-5">Status</th>
                <th className="py-3 px-5">Mode</th>
                <th className="py-3 px-5">Source Context</th>
                <th className="py-3 px-5 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12">
                    <EmptyState
                      icon={Clock}
                      title="No execution logs found"
                      description="No records matched your search or filter configuration."
                      actionLabel="Clear Filters"
                      onAction={() => {
                        setSearchTerm('')
                        setModeFilter('ALL')
                        setStatusFilter('ALL')
                        setPage(1)
                      }}
                    />
                  </td>
                </tr>
              ) : (
                logs.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => {
                      setSelectedLog(item)
                      setIsDrawerOpen(true)
                    }}
                    className="hover:bg-indigo-50/30 transition-colors cursor-pointer group"
                  >
                    <td className="py-3 px-5 font-mono text-xs text-slate-500 whitespace-nowrap">
                      {item.executed_at ? new Date(item.executed_at).toISOString().replace('T', ' ').slice(0, 19) : '—'}
                    </td>
                    <td className="py-3 px-5 font-mono text-xs font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors">
                      {item.recipient_email}
                    </td>
                    <td className="py-3 px-5 text-slate-700 max-w-xs truncate">
                      {item.subject}
                    </td>
                    <td className="py-3 px-5">
                      <StatusBadge status={item.execution_status} />
                    </td>
                    <td className="py-3 px-5">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium ${
                          item.execution_mode === 'LIVE_SMTP'
                            ? 'bg-indigo-100 text-indigo-700'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {item.execution_mode}
                      </span>
                    </td>
                    <td className="py-3 px-5 text-xs text-slate-500">
                      {item.campaign_name && (
                        <span className="text-indigo-600 font-medium block">
                          Campaign: {item.campaign_name}
                        </span>
                      )}
                      {item.reminder_title && (
                        <span className="text-teal-600 font-medium block">
                          Reminder: {item.reminder_title}
                        </span>
                      )}
                      {!item.campaign_name && !item.reminder_title && (
                        <span className="text-slate-400">Direct / Batch</span>
                      )}
                    </td>
                    <td className="py-3 px-5 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedLog(item)
                          setIsDrawerOpen(true)
                        }}
                      >
                        Inspect
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Audit Detail Slide-Over Drawer */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title="Audit Record Inspection"
        subtitle={selectedLog ? `Execution Log Record #${selectedLog.id}` : ''}
        size="md"
      >
        {selectedLog && (
          <div className="space-y-6">
            <div className="bg-slate-50 rounded-xl p-4 border border-slate-200">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Execution Outcome
              </h4>
              <div className="flex items-center justify-between">
                <StatusBadge status={selectedLog.execution_status} />
                <span className="text-xs font-mono font-semibold px-2 py-1 rounded bg-white border border-slate-200 text-slate-700">
                  {selectedLog.execution_mode}
                </span>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Message Content & Target
              </h4>
              <div className="p-4 rounded-xl border border-slate-200 bg-white space-y-2.5 text-sm">
                <div>
                  <span className="text-xs text-slate-400 block">Recipient Email:</span>
                  <span className="font-mono text-slate-900 font-semibold">{selectedLog.recipient_email}</span>
                </div>
                <div>
                  <span className="text-xs text-slate-400 block">Subject Line:</span>
                  <span className="text-slate-800 font-medium">{selectedLog.subject}</span>
                </div>
                {selectedLog.campaign_name && (
                  <div>
                    <span className="text-xs text-slate-400 block">Parent Campaign:</span>
                    <span className="text-indigo-600 font-medium">{selectedLog.campaign_name}</span>
                  </div>
                )}
                {selectedLog.reminder_title && (
                  <div>
                    <span className="text-xs text-slate-400 block">Reminder Job:</span>
                    <span className="text-teal-600 font-medium">{selectedLog.reminder_title}</span>
                  </div>
                )}
                <div className="flex justify-between pt-2 border-t border-slate-100 text-xs">
                  <span className="text-slate-500">Attempt Count:</span>
                  <span className="font-mono font-bold text-slate-800">{selectedLog.attempt_count}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Timestamp (UTC):</span>
                  <span className="font-mono text-slate-800">
                    {selectedLog.executed_at ? new Date(selectedLog.executed_at).toISOString() : '—'}
                  </span>
                </div>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Audit & Verification Identifiers
              </h4>
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 space-y-3 text-xs">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-slate-500 font-semibold">RFC 5322 Message-ID</span>
                    {selectedLog.message_id && (
                      <button
                        onClick={() => copyToClipboard(selectedLog.message_id!, 'msgId')}
                        className="text-[11px] text-indigo-600 hover:text-indigo-800 flex items-center space-x-1 font-semibold"
                      >
                        {copiedKey === 'msgId' ? <Check className="w-3 h-3 text-teal-600" /> : <Copy className="w-3 h-3" />}
                        <span>{copiedKey === 'msgId' ? 'Copied' : 'Copy'}</span>
                      </button>
                    )}
                  </div>
                  <p className="font-mono text-slate-900 bg-white p-2 rounded border border-slate-200 break-all">
                    {selectedLog.message_id || 'None (Simulated Dry-Run)'}
                  </p>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-slate-500 font-semibold">SMTP Server Queue ID</span>
                    {selectedLog.smtp_queue_id && (
                      <button
                        onClick={() => copyToClipboard(selectedLog.smtp_queue_id!, 'queueId')}
                        className="text-[11px] text-indigo-600 hover:text-indigo-800 flex items-center space-x-1 font-semibold"
                      >
                        {copiedKey === 'queueId' ? <Check className="w-3 h-3 text-teal-600" /> : <Copy className="w-3 h-3" />}
                        <span>{copiedKey === 'queueId' ? 'Copied' : 'Copy'}</span>
                      </button>
                    )}
                  </div>
                  <p className="font-mono text-slate-900 bg-white p-2 rounded border border-slate-200 break-all">
                    {selectedLog.smtp_queue_id || 'None'}
                  </p>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-slate-500 font-semibold">Provider Message ID</span>
                    {selectedLog.provider_message_id && (
                      <button
                        onClick={() => copyToClipboard(selectedLog.provider_message_id!, 'provId')}
                        className="text-[11px] text-indigo-600 hover:text-indigo-800 flex items-center space-x-1 font-semibold"
                      >
                        {copiedKey === 'provId' ? <Check className="w-3 h-3 text-teal-600" /> : <Copy className="w-3 h-3" />}
                        <span>{copiedKey === 'provId' ? 'Copied' : 'Copy'}</span>
                      </button>
                    )}
                  </div>
                  <p className="font-mono text-slate-900 bg-white p-2 rounded border border-slate-200 break-all">
                    {selectedLog.provider_message_id || 'None'}
                  </p>
                </div>
              </div>
            </div>

            {selectedLog.error_message && (
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-rose-500 mb-2">
                  Failure Diagnostics & SMTP Response
                </h4>
                <div className="p-4 rounded-xl border border-rose-200 bg-rose-50/50 space-y-2">
                  {selectedLog.error_category && (
                    <span className="inline-block px-2 py-0.5 bg-rose-100 text-rose-800 text-[11px] font-bold rounded">
                      {selectedLog.error_category}
                    </span>
                  )}
                  <p className="text-xs font-mono text-rose-900 break-words">
                    {selectedLog.error_message}
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </Drawer>
    </AppLayout>
  )
}
