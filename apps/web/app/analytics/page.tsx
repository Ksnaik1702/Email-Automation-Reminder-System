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
  BarChart3,
  TrendingUp,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Clock,
  HelpCircle,
  UserX,
  Download,
  Filter,
  RefreshCw,
  Calendar,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Layers,
  Activity,
  FileSpreadsheet
} from 'lucide-react'

interface OverviewMetrics {
  total_executions: number
  simulated_emails: number
  smtp_accepted: number
  delivery_confirmed: number
  failed_emails: number
  retry_pending: number
  delivery_uncertain: number
  skipped_inactive: number
  skipped_duplicate: number
  live_total: number
  delivery_rate: number
  failure_rate: number
}

interface TrendItem {
  date: string
  simulated: number
  live: number
  total: number
}

interface StatusDistributionItem {
  status: string
  count: number
  percentage: number
}

interface CampaignPerformanceItem {
  campaign_id: number | null
  campaign_name: string
  total_recipients: number
  total_logged: number
  simulated: number
  smtp_accepted: number
  delivery_confirmed: number
  failed: number
  retry_pending: number
  delivery_uncertain: number
  skipped_inactive: number
}

interface FailureCategoryItem {
  category: string
  count: number
}

interface TopErrorItem {
  error_message: string
  category?: string
  occurrences: number
  last_seen?: string
}

interface FailureAnalysis {
  categories: FailureCategoryItem[]
  top_errors: TopErrorItem[]
  total_failures: number
}

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

export default function AnalyticsDashboard() {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

  // Filter state
  const [startDate, setStartDate] = useState<string>('')
  const [endDate, setEndDate] = useState<string>('')
  const [selectedCampaignId, setSelectedCampaignId] = useState<string>('ALL')
  const [selectedMode, setSelectedMode] = useState<string>('ALL')
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL')
  const [searchQuery, setSearchQuery] = useState<string>('')

  // Pagination state
  const [page, setPage] = useState<number>(1)
  const [pageSize, setPageSize] = useState<number>(15)
  const [totalPages, setTotalPages] = useState<number>(1)
  const [totalCount, setTotalCount] = useState<number>(0)

  // Data state
  const [overview, setOverview] = useState<OverviewMetrics | null>(null)
  const [trends, setTrends] = useState<TrendItem[]>([])
  const [distribution, setDistribution] = useState<StatusDistributionItem[]>([])
  const [campaigns, setCampaigns] = useState<CampaignPerformanceItem[]>([])
  const [failures, setFailures] = useState<FailureAnalysis | null>(null)
  const [activity, setActivity] = useState<ActivityLogItem[]>([])
  const [availableCampaigns, setAvailableCampaigns] = useState<{ id: number; campaign_name: string }[]>([])

  // UI state
  const [loading, setLoading] = useState<boolean>(true)
  const [errorMsg, setErrorMsg] = useState<string>('')
  const [exporting, setExporting] = useState<boolean>(false)
  const [selectedLog, setSelectedLog] = useState<ActivityLogItem | null>(null)
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false)

  useEffect(() => {
    fetchAvailableCampaigns()
  }, [])

  useEffect(() => {
    fetchDashboardData()
  }, [startDate, endDate, selectedCampaignId, selectedMode, selectedStatus, page, pageSize])

  function buildFilterQuery(): string {
    const params = new URLSearchParams()
    if (startDate) params.set('start_date', startDate)
    if (endDate) params.set('end_date', endDate)
    if (selectedCampaignId !== 'ALL') params.set('campaign_id', selectedCampaignId)
    if (selectedMode !== 'ALL') params.set('execution_mode', selectedMode)
    if (selectedStatus !== 'ALL') params.set('status', selectedStatus)
    if (searchQuery.trim()) params.set('search', searchQuery.trim())
    return params.toString()
  }

  async function fetchAvailableCampaigns() {
    try {
      const res = await fetch(`${API_URL}/api/campaigns`)
      if (res.ok) {
        const data = await res.json()
        setAvailableCampaigns(data.items || [])
      }
    } catch (e) {
      console.warn('Could not load campaign filter list:', e)
    }
  }

  async function fetchDashboardData() {
    setLoading(true)
    setErrorMsg('')
    const q = buildFilterQuery()

    try {
      const [ovRes, trRes, distRes, campRes, failRes, actRes] = await Promise.all([
        fetch(`${API_URL}/api/analytics/overview?${q}`),
        fetch(`${API_URL}/api/analytics/trends?${q}`),
        fetch(`${API_URL}/api/analytics/status-distribution?${q}`),
        fetch(`${API_URL}/api/analytics/campaign-performance?${q}`),
        fetch(`${API_URL}/api/analytics/failures?${q}`),
        fetch(`${API_URL}/api/analytics/recent-activity?${q}&page=${page}&page_size=${pageSize}`)
      ])

      if (ovRes.ok) setOverview(await ovRes.json())
      if (trRes.ok) setTrends(await trRes.json())
      if (distRes.ok) setDistribution(await distRes.json())
      if (campRes.ok) setCampaigns(await campRes.json())
      if (failRes.ok) setFailures(await failRes.json())

      if (actRes.ok) {
        const actData = await actRes.json()
        setActivity(actData.items || [])
        setTotalPages(actData.total_pages || 1)
        setTotalCount(actData.total_count || 0)
      }
    } catch (e: any) {
      setErrorMsg(`Failed to load analytics: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  async function handleExport(exportType: string) {
    setExporting(true)
    try {
      const q = buildFilterQuery()
      const res = await fetch(`${API_URL}/api/analytics/export?export_type=${exportType}&${q}`)
      if (res.ok) {
        const blob = await res.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `analytics_${exportType}_${new Date().toISOString().slice(0, 10)}.csv`
        document.body.appendChild(a)
        a.click()
        a.remove()
        window.URL.revokeObjectURL(url)
      } else {
        alert('Export failed. Check server connection.')
      }
    } catch (e: any) {
      alert(`Export error: ${e.message}`)
    } finally {
      setExporting(false)
    }
  }

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault()
    setPage(1)
    fetchDashboardData()
  }

  function resetFilters() {
    setStartDate('')
    setEndDate('')
    setSelectedCampaignId('ALL')
    setSelectedMode('ALL')
    setSelectedStatus('ALL')
    setSearchQuery('')
    setPage(1)
  }

  const maxTrend = Math.max(...trends.map((t) => t.total), 1)

  return (
    <AppLayout
      title="Delivery Analytics & Reporting"
      subtitle="Execution volume, delivery metrics, SMTP reliability analysis, and exportable audit records"
      actions={
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            icon={<RefreshCw className="w-4 h-4" />}
            onClick={fetchDashboardData}
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            size="sm"
            icon={<Download className="w-4 h-4" />}
            loading={exporting}
            onClick={() => handleExport('complete')}
          >
            Export Audit CSV
          </Button>
        </div>
      }
    >
      {errorMsg && (
        <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-center justify-between shadow-sm">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            <span className="font-medium">{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg('')} className="text-rose-600 hover:text-rose-800 text-xs font-semibold">
            Dismiss
          </button>
        </div>
      )}

      {/* 8 Metric KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KPICard
          title="Total Executions"
          value={overview?.total_executions ?? 0}
          icon={BarChart3}
          trendText="All database dispatches"
          trendUp={true}
          accentColor="indigo"
          loading={loading}
        />
        <KPICard
          title="Simulated Emails"
          value={overview?.simulated_emails ?? 0}
          icon={ShieldCheck}
          trendText="Dry-run safety previews"
          trendUp={true}
          accentColor="teal"
          loading={loading}
        />
        <KPICard
          title="SMTP Accepted"
          value={overview?.smtp_accepted ?? 0}
          icon={TrendingUp}
          trendText="Relayed to SMTP host"
          trendUp={true}
          accentColor="blue"
          loading={loading}
        />
        <KPICard
          title="Delivery Confirmed"
          value={overview?.delivery_confirmed ?? 0}
          icon={CheckCircle2}
          trendText="Positive delivery receipts"
          trendUp={true}
          accentColor="green"
          loading={loading}
        />
        <KPICard
          title="Failed Emails"
          value={overview?.failed_emails ?? 0}
          icon={XCircle}
          trendText={overview ? `${overview.failure_rate.toFixed(1)}% failure rate` : ''}
          trendUp={false}
          accentColor="rose"
          loading={loading}
        />
        <KPICard
          title="Retry Pending"
          value={overview?.retry_pending ?? 0}
          icon={Clock}
          trendText="Queued with backoff"
          trendUp={false}
          accentColor="amber"
          loading={loading}
        />
        <KPICard
          title="Delivery Uncertain"
          value={overview?.delivery_uncertain ?? 0}
          icon={HelpCircle}
          trendText="Awaiting admin review"
          trendUp={false}
          accentColor="purple"
          loading={loading}
        />
        <KPICard
          title="Skipped Inactive"
          value={overview?.skipped_inactive ?? 0}
          icon={UserX}
          trendText="Terminated or leave status"
          trendUp={true}
          accentColor="blue"
          loading={loading}
        />
      </div>

      {/* Modern Filter Toolbar */}
      <div className="bg-white border border-slate-200/80 rounded-2xl p-5 mb-8 shadow-sm">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-indigo-600" />
            <span className="font-bold text-slate-800 text-sm">Dashboard Analytics Filters</span>
          </div>
          <button
            onClick={resetFilters}
            className="text-xs font-semibold text-slate-500 hover:text-indigo-600 transition-colors"
          >
            Reset All Filters
          </button>
        </div>

        <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <div>
            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => {
                setStartDate(e.target.value)
                setPage(1)
              }}
              className="w-full bg-slate-50 border border-slate-200 text-slate-700 text-xs rounded-xl px-3 py-2 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
              End Date
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => {
                setEndDate(e.target.value)
                setPage(1)
              }}
              className="w-full bg-slate-50 border border-slate-200 text-slate-700 text-xs rounded-xl px-3 py-2 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
              Campaign
            </label>
            <select
              value={selectedCampaignId}
              onChange={(e) => {
                setSelectedCampaignId(e.target.value)
                setPage(1)
              }}
              className="w-full bg-slate-50 border border-slate-200 text-slate-700 text-xs rounded-xl px-3 py-2 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            >
              <option value="ALL">All Campaigns</option>
              {availableCampaigns.map((c) => (
                <option key={c.id} value={String(c.id)}>
                  {c.campaign_name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
              Mode
            </label>
            <select
              value={selectedMode}
              onChange={(e) => {
                setSelectedMode(e.target.value)
                setPage(1)
              }}
              className="w-full bg-slate-50 border border-slate-200 text-slate-700 text-xs rounded-xl px-3 py-2 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            >
              <option value="ALL">All Modes</option>
              <option value="SIMULATION">Simulation</option>
              <option value="LIVE_SMTP">Live SMTP</option>
            </select>
          </div>

          <div>
            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
              Status
            </label>
            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value)
                setPage(1)
              }}
              className="w-full bg-slate-50 border border-slate-200 text-slate-700 text-xs rounded-xl px-3 py-2 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            >
              <option value="ALL">All Statuses</option>
              <option value="SIMULATED_SUCCESS">SIMULATED_SUCCESS</option>
              <option value="SMTP_ACCEPTED">SMTP_ACCEPTED</option>
              <option value="DELIVERY_CONFIRMED">DELIVERY_CONFIRMED</option>
              <option value="FAILED">FAILED</option>
              <option value="RETRY_PENDING">RETRY_PENDING</option>
              <option value="DELIVERY_UNCERTAIN">DELIVERY_UNCERTAIN</option>
              <option value="SKIPPED_INACTIVE">SKIPPED_INACTIVE</option>
            </select>
          </div>

          <div>
            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
              Search Text
            </label>
            <div className="flex space-x-1.5">
              <input
                type="text"
                placeholder="Email or subject..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 text-slate-700 text-xs rounded-xl px-3 py-2 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
              <Button variant="primary" size="sm" type="submit">
                Go
              </Button>
            </div>
          </div>
        </form>
      </div>

      {/* Visual Analytics Grid: Daily Trends & Status Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mb-8">
        {/* Daily Delivery Trends Chart */}
        <div className="lg:col-span-7 bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-100">
            <div>
              <h3 className="font-bold text-slate-900 text-base flex items-center space-x-2">
                <TrendingUp className="w-4 h-4 text-indigo-600" />
                <span>Daily Execution Volume Trends</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Simulated vs Live SMTP transmissions over time
              </p>
            </div>
            <div className="flex items-center space-x-3 text-xs">
              <span className="flex items-center space-x-1">
                <span className="w-3 h-3 rounded bg-teal-500 inline-block" />
                <span className="text-slate-600 font-medium">Simulated</span>
              </span>
              <span className="flex items-center space-x-1">
                <span className="w-3 h-3 rounded bg-indigo-600 inline-block" />
                <span className="text-slate-600 font-medium">Live SMTP</span>
              </span>
            </div>
          </div>

          {trends.length === 0 ? (
            <div className="py-16 text-center text-slate-400 text-xs">
              No daily trend data available for current date range.
            </div>
          ) : (
            <div className="space-y-4">
              <div className="h-48 flex items-end justify-between gap-2 pt-6">
                {trends.slice(-14).map((t) => {
                  const simPct = (t.simulated / maxTrend) * 100
                  const livePct = (t.live / maxTrend) * 100
                  return (
                    <div key={t.date} className="flex-1 flex flex-col items-center group relative h-full justify-end">
                      {/* Tooltip */}
                      <div className="opacity-0 group-hover:opacity-100 pointer-events-none absolute -top-10 bg-slate-900 text-white text-[10px] font-mono rounded px-2 py-1 shadow-md transition-opacity z-10 whitespace-nowrap">
                        {t.date}: {t.total} total ({t.simulated} sim, {t.live} live)
                      </div>

                      <div className="w-full max-w-[28px] flex flex-col justify-end h-full">
                        <div
                          style={{ height: `${livePct}%` }}
                          className="w-full bg-indigo-600 rounded-t-sm transition-all"
                        />
                        <div
                          style={{ height: `${simPct}%` }}
                          className="w-full bg-teal-500 rounded-b-sm transition-all"
                        />
                      </div>
                      <span className="text-[10px] font-mono text-slate-400 mt-2 rotate-45 origin-left">
                        {t.date.slice(5)}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        {/* Status Distribution Breakdown */}
        <div className="lg:col-span-5 bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-100">
            <div>
              <h3 className="font-bold text-slate-900 text-base flex items-center space-x-2">
                <Activity className="w-4 h-4 text-indigo-600" />
                <span>Execution Status Distribution</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Outcome breakdown with computed percentage shares
              </p>
            </div>
          </div>

          <div className="space-y-4">
            {distribution.map((item) => (
              <div key={item.status} className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2">
                    <StatusBadge status={item.status} />
                    <span className="font-mono text-slate-500">{item.count}</span>
                  </div>
                  <span className="font-bold text-slate-700">{item.percentage.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      item.status.includes('SUCCESS') || item.status.includes('CONFIRMED')
                        ? 'bg-teal-500'
                        : item.status.includes('FAILED')
                        ? 'bg-rose-500'
                        : item.status.includes('RETRY')
                        ? 'bg-amber-500'
                        : item.status.includes('UNCERTAIN')
                        ? 'bg-purple-500'
                        : 'bg-indigo-500'
                    }`}
                    style={{ width: `${Math.min(item.percentage, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Campaign Performance Table */}
      <div className="bg-white border border-slate-200/80 rounded-2xl shadow-sm mb-8 overflow-hidden">
        <div className="p-6 pb-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="font-bold text-slate-900 text-base flex items-center space-x-2">
              <Layers className="w-4 h-4 text-indigo-600" />
              <span>Campaign Delivery Performance</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Target audience delivery rates, simulated dispatches, and failure ratios
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            icon={<FileSpreadsheet className="w-3.5 h-3.5" />}
            onClick={() => handleExport('campaigns')}
          >
            Export Campaign CSV
          </Button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="bg-slate-50/75 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-5">Campaign Name</th>
                <th className="py-3 px-5">Target Recipients</th>
                <th className="py-3 px-5">Simulated</th>
                <th className="py-3 px-5">SMTP Accepted</th>
                <th className="py-3 px-5">Confirmed</th>
                <th className="py-3 px-5">Failed</th>
                <th className="py-3 px-5">Uncertain</th>
                <th className="py-3 px-5">Skipped Inactive</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {campaigns.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-xs text-slate-400">
                    No campaign execution data found.
                  </td>
                </tr>
              ) : (
                campaigns.map((c) => (
                  <tr key={c.campaign_id || c.campaign_name} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-3 px-5 font-semibold text-slate-900">
                      {c.campaign_name}
                      {c.campaign_id && (
                        <span className="block text-[11px] font-mono text-slate-400">
                          ID: #{c.campaign_id}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-5 font-mono text-xs">{c.total_recipients}</td>
                    <td className="py-3 px-5 font-mono text-xs text-teal-700 font-semibold">{c.simulated}</td>
                    <td className="py-3 px-5 font-mono text-xs text-indigo-700 font-semibold">{c.smtp_accepted}</td>
                    <td className="py-3 px-5 font-mono text-xs text-green-700 font-semibold">{c.delivery_confirmed}</td>
                    <td className="py-3 px-5 font-mono text-xs text-rose-700 font-semibold">{c.failed}</td>
                    <td className="py-3 px-5 font-mono text-xs text-purple-700 font-semibold">{c.delivery_uncertain}</td>
                    <td className="py-3 px-5 font-mono text-xs text-slate-400">{c.skipped_inactive}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Failure Root-Cause Analysis */}
      {failures && failures.categories.length > 0 && (
        <div className="bg-white border border-slate-200/80 rounded-2xl shadow-sm mb-8 overflow-hidden p-6">
          <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100">
            <div>
              <h3 className="font-bold text-slate-900 text-base flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-rose-600" />
                <span>Failure Diagnostics & Root Cause Analysis</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Classified error categories and recurring failure messages
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              icon={<Download className="w-3.5 h-3.5" />}
              onClick={() => handleExport('failures')}
            >
              Export Failures CSV
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                Failures by Error Category
              </h4>
              <div className="space-y-2">
                {failures.categories.map((cat) => (
                  <div key={cat.category} className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200/70 text-xs">
                    <span className="font-semibold text-slate-700">{cat.category}</span>
                    <span className="font-mono font-bold text-rose-600 px-2 py-0.5 rounded bg-rose-50 border border-rose-200">
                      {cat.count} occurrences
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                Top Recurring Errors
              </h4>
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {failures.top_errors.map((err, i) => (
                  <div key={i} className="p-3 rounded-xl bg-rose-50/40 border border-rose-100 text-xs">
                    <p className="font-mono text-slate-800 break-words">{err.error_message}</p>
                    <div className="flex items-center justify-between mt-1 text-[11px] text-slate-500 font-mono">
                      <span>Seen {err.occurrences}x</span>
                      {err.category && <span className="text-rose-600">{err.category}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Paginated Recent Activity Log */}
      <div className="bg-white border border-slate-200/80 rounded-2xl shadow-sm overflow-hidden">
        <div className="p-6 pb-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="font-bold text-slate-900 text-base flex items-center space-x-2">
              <Clock className="w-4 h-4 text-indigo-600" />
              <span>Recent Activity Stream</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Showing {activity.length} of {totalCount} total audit records
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
                <th className="py-3 px-5">Executed At (UTC)</th>
                <th className="py-3 px-5">Recipient</th>
                <th className="py-3 px-5">Subject</th>
                <th className="py-3 px-5">Mode</th>
                <th className="py-3 px-5">Status</th>
                <th className="py-3 px-5">Attempts</th>
                <th className="py-3 px-5 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {activity.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center">
                    <EmptyState
                      icon={Clock}
                      title="No execution logs found"
                      description="No audit records match your selected criteria."
                    />
                  </td>
                </tr>
              ) : (
                activity.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => {
                      setSelectedLog(item)
                      setIsDrawerOpen(true)
                    }}
                    className="hover:bg-indigo-50/30 transition-colors cursor-pointer group"
                  >
                    <td className="py-3 px-5 font-mono text-xs text-slate-500 whitespace-nowrap">
                      {item.executed_at ? new Date(item.executed_at).toLocaleString() : '—'}
                    </td>
                    <td className="py-3 px-5 font-medium text-slate-900 group-hover:text-indigo-600 transition-colors">
                      {item.recipient_email}
                      {item.campaign_name && (
                        <span className="block text-[11px] text-slate-400">
                          {item.campaign_name}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-5 text-slate-700 max-w-xs truncate">
                      {item.subject}
                    </td>
                    <td className="py-3 px-5">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-slate-100 text-slate-700">
                        {item.execution_mode}
                      </span>
                    </td>
                    <td className="py-3 px-5">
                      <StatusBadge status={item.execution_status} />
                    </td>
                    <td className="py-3 px-5 font-mono text-xs text-center">
                      {item.attempt_count}
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

      {/* Log Detail Drawer */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title="Execution Audit Record"
        subtitle={selectedLog ? `Log Record #${selectedLog.id}` : ''}
        size="md"
      >
        {selectedLog && (
          <div className="space-y-6">
            <div className="bg-slate-50 rounded-xl p-4 border border-slate-200">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Execution Status
              </h4>
              <div className="flex items-center justify-between">
                <StatusBadge status={selectedLog.execution_status} />
                <span className="text-xs font-mono text-slate-500">
                  Mode: {selectedLog.execution_mode}
                </span>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Email Message Details
              </h4>
              <div className="p-4 rounded-xl border border-slate-200 bg-white space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-500">Recipient:</span>
                  <span className="font-mono text-slate-900">{selectedLog.recipient_email}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Subject:</span>
                  <span className="font-semibold text-slate-900">{selectedLog.subject}</span>
                </div>
                {selectedLog.campaign_name && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">Campaign:</span>
                    <span className="text-indigo-600 font-medium">{selectedLog.campaign_name}</span>
                  </div>
                )}
                {selectedLog.reminder_title && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">Reminder:</span>
                    <span className="text-indigo-600 font-medium">{selectedLog.reminder_title}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-slate-500">Attempts:</span>
                  <span className="font-mono text-slate-800">{selectedLog.attempt_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Timestamp:</span>
                  <span className="font-mono text-slate-800">
                    {selectedLog.executed_at ? new Date(selectedLog.executed_at).toISOString() : '—'}
                  </span>
                </div>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Technical Message Identifiers
              </h4>
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2 text-xs font-mono">
                <div>
                  <span className="text-slate-400 block mb-0.5">RFC 5322 Message-ID:</span>
                  <span className="text-slate-900 break-all">{selectedLog.message_id || 'None (Simulated)'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block mb-0.5">SMTP Server Queue ID:</span>
                  <span className="text-slate-900 break-all">{selectedLog.smtp_queue_id || 'None'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block mb-0.5">Provider Message ID:</span>
                  <span className="text-slate-900 break-all">{selectedLog.provider_message_id || 'None'}</span>
                </div>
              </div>
            </div>

            {selectedLog.error_message && (
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-rose-500 mb-2">
                  Failure Diagnostics
                </h4>
                <div className="p-4 rounded-xl border border-rose-200 bg-rose-50/50 space-y-1">
                  {selectedLog.error_category && (
                    <span className="inline-block px-2 py-0.5 bg-rose-100 text-rose-800 text-[11px] font-bold rounded">
                      {selectedLog.error_category}
                    </span>
                  )}
                  <p className="text-xs font-mono text-rose-900 mt-2 break-words">
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
