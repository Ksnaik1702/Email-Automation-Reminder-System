'use client'

import React, { useState, useEffect } from 'react'

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
      // 1. Overview KPIs
      const overviewRes = await fetch(`${API_URL}/api/analytics/overview?${q}`)
      if (overviewRes.ok) setOverview(await overviewRes.json())

      // 2. Daily Trends
      const trendsRes = await fetch(`${API_URL}/api/analytics/trends?${q}`)
      if (trendsRes.ok) setTrends(await trendsRes.json())

      // 3. Status Distribution
      const distRes = await fetch(`${API_URL}/api/analytics/status-distribution?${q}`)
      if (distRes.ok) setDistribution(await distRes.json())

      // 4. Campaign Performance
      const campRes = await fetch(`${API_URL}/api/analytics/campaign-performance?${q}`)
      if (campRes.ok) setCampaigns(await campRes.json())

      // 5. Failures
      const failRes = await fetch(`${API_URL}/api/analytics/failures?${q}`)
      if (failRes.ok) setFailures(await failRes.json())

      // 6. Recent Activity (Paginated)
      const actRes = await fetch(`${API_URL}/api/analytics/recent-activity?${q}&page=${page}&page_size=${pageSize}`)
      if (actRes.ok) {
        const actData = await actRes.json()
        setActivity(actData.items || [])
        setTotalPages(actData.total_pages || 1)
        setTotalCount(actData.total_count || 0)
      }
    } catch (err: any) {
      setErrorMsg(`Failed to connect to Analytics API: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault()
    setPage(1)
    fetchDashboardData()
  }

  function handleResetFilters() {
    setStartDate('')
    setEndDate('')
    setSelectedCampaignId('ALL')
    setSelectedMode('ALL')
    setSelectedStatus('ALL')
    setSearchQuery('')
    setPage(1)
  }

  async function handleDownloadCsv(type: string) {
    setExporting(true)
    try {
      const q = buildFilterQuery()
      const url = `${API_URL}/api/analytics/export?export_type=${type}&${q}`
      const res = await fetch(url)
      if (!res.ok) {
        throw new Error(`Export failed with HTTP ${res.status}`)
      }
      const blob = await res.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = downloadUrl

      const disposition = res.headers.get('content-disposition')
      let filename = `report_${type}.csv`
      if (disposition && disposition.includes('filename=')) {
        filename = disposition.split('filename=')[1].replace(/"/g, '').trim()
      }
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(downloadUrl)
    } catch (err: any) {
      alert(`Export error: ${err.message}`)
    } finally {
      setExporting(false)
    }
  }

  function getStatusBadge(status: string) {
    let bg = '#f1f5f9'
    let text = '#475569'
    let border = '#cbd5e1'

    switch (status) {
      case 'SMTP_ACCEPTED':
        bg = '#f0fdf4'; text = '#166534'; border = '#bbf7d0'; break
      case 'DELIVERY_CONFIRMED':
        bg = '#ecfdf5'; text = '#065f46'; border = '#a7f3d0'; break
      case 'SIMULATED_SUCCESS':
        bg = '#eff6ff'; text = '#1e40af'; border = '#bfdbfe'; break
      case 'FAILED':
        bg = '#fef2f2'; text = '#991b1b'; border = '#fecaca'; break
      case 'RETRY_PENDING':
        bg = '#fffbeb'; text = '#92400e'; border = '#fde68a'; break
      case 'DELIVERY_UNCERTAIN':
        bg = '#faf5ff'; text = '#6b21a8'; border = '#e9d5ff'; break
      case 'SKIPPED_INACTIVE':
        bg = '#f8fafc'; text = '#64748b'; border = '#e2e8f0'; break
    }

    return (
      <span style={{
        display: 'inline-block',
        padding: '3px 8px',
        fontSize: 11,
        fontWeight: 600,
        borderRadius: 4,
        background: bg,
        color: text,
        border: `1px solid ${border}`,
        whiteSpace: 'nowrap'
      }}>
        {status}
      </span>
    )
  }

  function getModeBadge(mode: string) {
    const isLive = mode === 'LIVE_SMTP'
    return (
      <span style={{
        display: 'inline-block',
        padding: '2px 6px',
        fontSize: 10,
        fontWeight: 700,
        borderRadius: 4,
        background: isLive ? '#fef3c7' : '#e0f2fe',
        color: isLive ? '#92400e' : '#0369a1',
        border: `1px solid ${isLive ? '#fcd34d' : '#bae6fd'}`,
        letterSpacing: '0.04em'
      }}>
        {isLive ? 'LIVE' : 'SIMULATION'}
      </span>
    )
  }

  return (
    <div style={{ maxWidth: 1280, margin: '0 auto', padding: '32px 20px', fontFamily: 'system-ui, -apple-system, sans-serif', color: '#0f172a' }}>

      {/* Top Header & Breadcrumbs */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24, borderBottom: '1px solid #e2e8f0', paddingBottom: 20, flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 6, fontSize: 13, color: '#64748b' }}>
            <a href="/" style={{ color: '#64748b', textDecoration: 'none' }}>Home</a>
            <span>/</span>
            <a href="/employees" style={{ color: '#64748b', textDecoration: 'none' }}>Workforce</a>
            <span>/</span>
            <a href="/templates" style={{ color: '#64748b', textDecoration: 'none' }}>Templates</a>
            <span>/</span>
            <a href="/campaigns" style={{ color: '#64748b', textDecoration: 'none' }}>Campaigns</a>
            <span>/</span>
            <span style={{ fontWeight: 600, color: '#0f172a' }}>Delivery Analytics</span>
          </div>
          <h1 style={{ fontSize: 26, fontWeight: 700, margin: 0, color: '#0f172a' }}>
            Delivery Analytics &amp; Reporting
          </h1>
          <p style={{ color: '#64748b', margin: '4px 0 0 0', fontSize: 14 }}>
            Real-time delivery telemetry, campaign performance audit trails, failure root-cause analysis, and compliance exports.
          </p>
        </div>

        {/* CSV Export Quick Actions */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            onClick={() => handleDownloadCsv('complete')}
            disabled={exporting}
            style={{ backgroundColor: '#0f172a', color: '#fff', border: 'none', borderRadius: 6, padding: '8px 14px', fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}
            title="Download full audit log respecting active filters"
          >
            📥 Full Audit CSV
          </button>
          <button
            onClick={() => handleDownloadCsv('campaigns')}
            disabled={exporting}
            style={{ backgroundColor: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, padding: '8px 14px', fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}
            title="Download campaign delivery breakdown"
          >
            📊 Campaigns CSV
          </button>
          <button
            onClick={() => handleDownloadCsv('failures')}
            disabled={exporting}
            style={{ backgroundColor: '#dc2626', color: '#fff', border: 'none', borderRadius: 6, padding: '8px 14px', fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}
            title="Export error log for troubleshooting"
          >
            ⚠️ Failures CSV
          </button>
          <button
            onClick={() => handleDownloadCsv('uncertain')}
            disabled={exporting}
            style={{ backgroundColor: '#7c3aed', color: '#fff', border: 'none', borderRadius: 6, padding: '8px 14px', fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}
            title="Export uncertain delivery attempts"
          >
            ❓ Uncertain CSV
          </button>
        </div>
      </header>

      {/* Error alert banner */}
      {errorMsg && (
        <div style={{ padding: '12px 16px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 6, marginBottom: 20, color: '#991b1b', fontSize: 13 }}>
          {errorMsg}
        </div>
      )}

      {/* Filter & Search Bar */}
      <section style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '16px 20px', marginBottom: 24, boxShadow: '0 1px 2px rgba(0,0,0,0.03)' }}>
        <form onSubmit={handleSearchSubmit} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 12, alignItems: 'flex-end' }}>
          
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>From Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => { setStartDate(e.target.value); setPage(1); }}
              style={{ width: '100%', padding: '7px 10px', fontSize: 13, border: '1px solid #cbd5e1', borderRadius: 6, boxSizing: 'border-box' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>To Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => { setEndDate(e.target.value); setPage(1); }}
              style={{ width: '100%', padding: '7px 10px', fontSize: 13, border: '1px solid #cbd5e1', borderRadius: 6, boxSizing: 'border-box' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Campaign</label>
            <select
              value={selectedCampaignId}
              onChange={(e) => { setSelectedCampaignId(e.target.value); setPage(1); }}
              style={{ width: '100%', padding: '7px 10px', fontSize: 13, border: '1px solid #cbd5e1', borderRadius: 6, background: '#fff' }}
            >
              <option value="ALL">All Campaigns</option>
              {availableCampaigns.map(c => (
                <option key={c.id} value={c.id}>{c.campaign_name}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Mode</label>
            <select
              value={selectedMode}
              onChange={(e) => { setSelectedMode(e.target.value); setPage(1); }}
              style={{ width: '100%', padding: '7px 10px', fontSize: 13, border: '1px solid #cbd5e1', borderRadius: 6, background: '#fff' }}
            >
              <option value="ALL">All Modes</option>
              <option value="SIMULATION">Simulation (Dry-Run)</option>
              <option value="LIVE_SMTP">Live SMTP Delivery</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Status</label>
            <select
              value={selectedStatus}
              onChange={(e) => { setSelectedStatus(e.target.value); setPage(1); }}
              style={{ width: '100%', padding: '7px 10px', fontSize: 13, border: '1px solid #cbd5e1', borderRadius: 6, background: '#fff' }}
            >
              <option value="ALL">All Statuses</option>
              <option value="SMTP_ACCEPTED">SMTP_ACCEPTED</option>
              <option value="DELIVERY_CONFIRMED">DELIVERY_CONFIRMED</option>
              <option value="SIMULATED_SUCCESS">SIMULATED_SUCCESS</option>
              <option value="FAILED">FAILED</option>
              <option value="RETRY_PENDING">RETRY_PENDING</option>
              <option value="DELIVERY_UNCERTAIN">DELIVERY_UNCERTAIN</option>
              <option value="SKIPPED_INACTIVE">SKIPPED_INACTIVE</option>
            </select>
          </div>

          <div style={{ gridColumn: 'span 2' }}>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Search Recipient / Subject</label>
            <div style={{ display: 'flex', gap: 6 }}>
              <input
                type="text"
                placeholder="e.g. kiran.patel@testcorp.com or Welcome"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ flex: 1, padding: '7px 10px', fontSize: 13, border: '1px solid #cbd5e1', borderRadius: 6 }}
              />
              <button
                type="submit"
                style={{ backgroundColor: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, padding: '7px 14px', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
              >
                Search
              </button>
              <button
                type="button"
                onClick={handleResetFilters}
                style={{ backgroundColor: '#f1f5f9', color: '#475569', border: '1px solid #cbd5e1', borderRadius: 6, padding: '7px 12px', fontSize: 13, cursor: 'pointer' }}
              >
                Reset
              </button>
            </div>
          </div>

        </form>
      </section>

      {/* KPI Cards Grid */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(135px, 1fr))', gap: 12, marginBottom: 24 }}>
        
        {/* 1. Total Executions */}
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '14px 16px', boxShadow: '0 1px 2px rgba(0,0,0,0.02)' }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Total Executions</span>
          <div style={{ fontSize: 24, fontWeight: 700, color: '#0f172a', marginTop: 4 }}>
            {overview ? overview.total_executions : '-'}
          </div>
          <span style={{ fontSize: 11, color: '#94a3b8' }}>All Dispatches</span>
        </div>

        {/* 2. Simulated Emails */}
        <div style={{ background: '#fff', border: '1px solid #bfdbfe', borderRadius: 8, padding: '14px 16px', boxShadow: '0 1px 2px rgba(0,0,0,0.02)' }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#1e40af', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Simulated</span>
          <div style={{ fontSize: 24, fontWeight: 700, color: '#1e40af', marginTop: 4 }}>
            {overview ? overview.simulated_emails : '-'}
          </div>
          <span style={{ fontSize: 11, color: '#3b82f6' }}>Virtual Sandbox</span>
        </div>

        {/* 3. SMTP Accepted */}
        <div style={{ background: '#fff', border: '1px solid #bbf7d0', borderRadius: 8, padding: '14px 16px', boxShadow: '0 1px 2px rgba(0,0,0,0.02)' }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#166534', textTransform: 'uppercase', letterSpacing: '0.04em' }}>SMTP Accepted</span>
          <div style={{ fontSize: 24, fontWeight: 700, color: '#166534', marginTop: 4 }}>
            {overview ? overview.smtp_accepted : '-'}
          </div>
          <span style={{ fontSize: 11, color: '#16a34a' }}>Relayed by MTA</span>
        </div>

        {/* 4. Delivery Confirmed */}
        <div style={{ background: '#fff', border: '1px solid #a7f3d0', borderRadius: 8, padding: '14px 16px', boxShadow: '0 1px 2px rgba(0,0,0,0.02)' }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#065f46', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Confirmed</span>
          <div style={{ fontSize: 24, fontWeight: 700, color: '#065f46', marginTop: 4 }}>
            {overview ? overview.delivery_confirmed : '-'}
          </div>
          <span style={{ fontSize: 11, color: '#059669' }}>Verified Inbox</span>
        </div>

        {/* 5. Failed Emails */}
        <div style={{ background: '#fff', border: '1px solid #fecaca', borderRadius: 8, padding: '14px 16px', boxShadow: '0 1px 2px rgba(0,0,0,0.02)' }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#991b1b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Failed</span>
          <div style={{ fontSize: 24, fontWeight: 700, color: '#991b1b', marginTop: 4 }}>
            {overview ? overview.failed_emails : '-'}
          </div>
          <span style={{ fontSize: 11, color: '#dc2626' }}>Terminal Errors</span>
        </div>

        {/* 6. Retry Pending */}
        <div style={{ background: '#fff', border: '1px solid #fde68a', borderRadius: 8, padding: '14px 16px', boxShadow: '0 1px 2px rgba(0,0,0,0.02)' }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#92400e', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Retry Pending</span>
          <div style={{ fontSize: 24, fontWeight: 700, color: '#92400e', marginTop: 4 }}>
            {overview ? overview.retry_pending : '-'}
          </div>
          <span style={{ fontSize: 11, color: '#d97706' }}>In Backoff Queue</span>
        </div>

        {/* 7. Delivery Uncertain */}
        <div style={{ background: '#fff', border: '1px solid #e9d5ff', borderRadius: 8, padding: '14px 16px', boxShadow: '0 1px 2px rgba(0,0,0,0.02)' }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#6b21a8', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Uncertain</span>
          <div style={{ fontSize: 24, fontWeight: 700, color: '#6b21a8', marginTop: 4 }}>
            {overview ? overview.delivery_uncertain : '-'}
          </div>
          <span style={{ fontSize: 11, color: '#9333ea' }}>Post-Sub Timeout</span>
        </div>

        {/* 8. Skipped Inactive */}
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '14px 16px', boxShadow: '0 1px 2px rgba(0,0,0,0.02)' }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Skipped Inact.</span>
          <div style={{ fontSize: 24, fontWeight: 700, color: '#475569', marginTop: 4 }}>
            {overview ? overview.skipped_inactive : '-'}
          </div>
          <span style={{ fontSize: 11, color: '#94a3b8' }}>Safety Filter</span>
        </div>

      </section>

      {/* Rates Bar */}
      {overview && overview.live_total > 0 && (
        <div style={{ display: 'flex', gap: 20, background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: '12px 18px', marginBottom: 24, fontSize: 13, alignItems: 'center' }}>
          <div>
            <strong style={{ color: '#0f172a' }}>Live Transmissions Evaluated:</strong> {overview.live_total}
          </div>
          <div>
            <strong style={{ color: '#166534' }}>Delivery Rate:</strong> {overview.delivery_rate}%
          </div>
          <div>
            <strong style={{ color: '#991b1b' }}>Failure Rate:</strong> {overview.failure_rate}%
          </div>
        </div>
      )}

      {/* Visualizations Section: Trends & Distribution */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 20, marginBottom: 28 }}>
        
        {/* A. Execution Trends Timeline */}
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '18px 20px', boxShadow: '0 1px 2px rgba(0,0,0,0.02)' }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 12px 0', color: '#0f172a' }}>
            Daily Execution Volume
          </h2>
          <p style={{ fontSize: 12, color: '#64748b', margin: '0 0 16px 0' }}>
            Volume breakdown across simulation dry-runs and live SMTP dispatches.
          </p>

          {trends.length === 0 ? (
            <div style={{ padding: '36px 0', textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>
              No execution records in selected date range.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {trends.map(t => {
                const maxTotal = Math.max(...trends.map(x => x.total), 1)
                const simPct = Math.round((t.simulated / maxTotal) * 100)
                const livePct = Math.round((t.live / maxTotal) * 100)

                return (
                  <div key={t.date} style={{ fontSize: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3, fontWeight: 600 }}>
                      <span style={{ color: '#334155' }}>{t.date}</span>
                      <span style={{ color: '#64748b' }}>
                        Total: <strong>{t.total}</strong> (Sim: {t.simulated}, Live: {t.live})
                      </span>
                    </div>
                    {/* Stacked Visual Bar */}
                    <div style={{ height: 14, width: '100%', background: '#f1f5f9', borderRadius: 4, overflow: 'hidden', display: 'flex' }}>
                      <div style={{ width: `${simPct}%`, background: '#3b82f6' }} title={`Simulated: ${t.simulated}`} />
                      <div style={{ width: `${livePct}%`, background: '#10b981' }} title={`Live: ${t.live}`} />
                    </div>
                  </div>
                )
              })}
              <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 11, color: '#64748b' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ width: 10, height: 10, background: '#3b82f6', borderRadius: 2 }} /> Simulated
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ width: 10, height: 10, background: '#10b981', borderRadius: 2 }} /> Live SMTP
                </span>
              </div>
            </div>
          )}
        </div>

        {/* B. Delivery Status Distribution */}
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '18px 20px', boxShadow: '0 1px 2px rgba(0,0,0,0.02)' }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 12px 0', color: '#0f172a' }}>
            Status Distribution
          </h2>
          <p style={{ fontSize: 12, color: '#64748b', margin: '0 0 16px 0' }}>
            Proportion of all processed messages categorized by final execution status.
          </p>

          {distribution.length === 0 ? (
            <div style={{ padding: '36px 0', textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>
              No status distribution data available.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {distribution.map(d => (
                <div key={d.status} style={{ fontSize: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontWeight: 600 }}>
                    <span>{getStatusBadge(d.status)}</span>
                    <span style={{ color: '#475569' }}>
                      {d.count} ({d.percentage}%)
                    </span>
                  </div>
                  <div style={{ height: 8, width: '100%', background: '#f1f5f9', borderRadius: 4, overflow: 'hidden' }}>
                    <div
                      style={{
                        height: '100%',
                        width: `${d.percentage}%`,
                        background:
                          d.status === 'SMTP_ACCEPTED' ? '#16a34a' :
                          d.status === 'DELIVERY_CONFIRMED' ? '#059669' :
                          d.status === 'SIMULATED_SUCCESS' ? '#2563eb' :
                          d.status === 'FAILED' ? '#dc2626' :
                          d.status === 'RETRY_PENDING' ? '#d97706' :
                          d.status === 'DELIVERY_UNCERTAIN' ? '#9333ea' : '#94a3b8'
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </section>

      {/* C. Campaign Performance Breakdown */}
      <section style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '20px', marginBottom: 28, boxShadow: '0 1px 2px rgba(0,0,0,0.02)' }}>
        <h2 style={{ fontSize: 17, fontWeight: 700, margin: '0 0 4px 0', color: '#0f172a' }}>
          Campaign Performance Summary
        </h2>
        <p style={{ fontSize: 12, color: '#64748b', margin: '0 0 16px 0' }}>
          Aggregate recipient fulfillment, acceptance, failures, and retry statuses per campaign.
        </p>

        {campaigns.length === 0 ? (
          <div style={{ padding: '24px 0', textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>
            No campaign activity found matching criteria.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e2e8f0', color: '#64748b', fontSize: 11, textTransform: 'uppercase' }}>
                  <th style={{ padding: '8px 12px' }}>Campaign Name</th>
                  <th style={{ padding: '8px 10px', textAlign: 'right' }}>Targeted</th>
                  <th style={{ padding: '8px 10px', textAlign: 'right' }}>Logged</th>
                  <th style={{ padding: '8px 10px', textAlign: 'right' }}>Simulated</th>
                  <th style={{ padding: '8px 10px', textAlign: 'right' }}>Accepted</th>
                  <th style={{ padding: '8px 10px', textAlign: 'right' }}>Confirmed</th>
                  <th style={{ padding: '8px 10px', textAlign: 'right' }}>Failed</th>
                  <th style={{ padding: '8px 10px', textAlign: 'right' }}>Retrying</th>
                  <th style={{ padding: '8px 10px', textAlign: 'right' }}>Uncertain</th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map(c => (
                  <tr key={c.campaign_id || 'unlinked'} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '10px 12px', fontWeight: 600, color: '#0f172a' }}>
                      {c.campaign_name}
                      {c.campaign_id && <span style={{ marginLeft: 6, fontSize: 11, color: '#94a3b8' }}>#{c.campaign_id}</span>}
                    </td>
                    <td style={{ padding: '10px 10px', textAlign: 'right', color: '#475569' }}>{c.total_recipients}</td>
                    <td style={{ padding: '10px 10px', textAlign: 'right', fontWeight: 700 }}>{c.total_logged}</td>
                    <td style={{ padding: '10px 10px', textAlign: 'right', color: '#2563eb' }}>{c.simulated}</td>
                    <td style={{ padding: '10px 10px', textAlign: 'right', color: '#16a34a', fontWeight: 600 }}>{c.smtp_accepted}</td>
                    <td style={{ padding: '10px 10px', textAlign: 'right', color: '#059669', fontWeight: 600 }}>{c.delivery_confirmed}</td>
                    <td style={{ padding: '10px 10px', textAlign: 'right', color: c.failed > 0 ? '#dc2626' : '#94a3b8', fontWeight: c.failed > 0 ? 700 : 400 }}>
                      {c.failed}
                    </td>
                    <td style={{ padding: '10px 10px', textAlign: 'right', color: c.retry_pending > 0 ? '#d97706' : '#94a3b8' }}>
                      {c.retry_pending}
                    </td>
                    <td style={{ padding: '10px 10px', textAlign: 'right', color: c.delivery_uncertain > 0 ? '#9333ea' : '#94a3b8', fontWeight: c.delivery_uncertain > 0 ? 700 : 400 }}>
                      {c.delivery_uncertain}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* D. Failure Analysis */}
      <section style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '20px', marginBottom: 28, boxShadow: '0 1px 2px rgba(0,0,0,0.02)' }}>
        <h2 style={{ fontSize: 17, fontWeight: 700, margin: '0 0 4px 0', color: '#0f172a' }}>
          Failure Diagnostics &amp; Error Analysis
        </h2>
        <p style={{ fontSize: 12, color: '#64748b', margin: '0 0 16px 0' }}>
          Categorized root-cause classification and recurring error diagnosis.
        </p>

        {(!failures || failures.total_failures === 0) ? (
          <div style={{ padding: '24px 16px', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 6, color: '#166534', fontSize: 13, textAlign: 'center' }}>
            🎉 <strong>Zero Failures Recorded:</strong> All message execution attempts in the selected range concluded successfully or are in valid simulation.
          </div>
        ) : (
          <div>
            {/* Category Badges */}
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
              {failures.categories.map(cat => (
                <div key={cat.category} style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 6, padding: '8px 12px', fontSize: 12 }}>
                  <span style={{ fontWeight: 700, color: '#991b1b' }}>{cat.category}:</span>{' '}
                  <span style={{ color: '#b91c1c', fontWeight: 600 }}>{cat.count} occurrence(s)</span>
                </div>
              ))}
            </div>

            {/* Top Error Messages Table */}
            {failures.top_errors.length > 0 && (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #e2e8f0', color: '#64748b', textTransform: 'uppercase', fontSize: 11 }}>
                      <th style={{ padding: '6px 10px' }}>Error Diagnostic Detail</th>
                      <th style={{ padding: '6px 10px' }}>Category</th>
                      <th style={{ padding: '6px 10px', textAlign: 'right' }}>Occurrences</th>
                      <th style={{ padding: '6px 10px', textAlign: 'right' }}>Last Seen (UTC)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {failures.top_errors.map((err, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '8px 10px', color: '#991b1b', fontFamily: 'monospace', maxWidth: 450, wordBreak: 'break-word' }}>
                          {err.error_message}
                        </td>
                        <td style={{ padding: '8px 10px', color: '#475569' }}>{err.category}</td>
                        <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 700 }}>{err.occurrences}</td>
                        <td style={{ padding: '8px 10px', textAlign: 'right', color: '#64748b' }}>
                          {err.last_seen ? new Date(err.last_seen).toLocaleString() : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </section>

      {/* E. Recent Activity Log (Paginated) */}
      <section style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '20px', boxShadow: '0 1px 2px rgba(0,0,0,0.02)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
          <div>
            <h2 style={{ fontSize: 17, fontWeight: 700, margin: '0 0 2px 0', color: '#0f172a' }}>
              Recent Execution Activity
            </h2>
            <span style={{ fontSize: 12, color: '#64748b' }}>
              Showing {activity.length} of {totalCount} matching execution records
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
            <label style={{ color: '#64748b' }}>Rows per page:</label>
            <select
              value={pageSize}
              onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}
              style={{ padding: '4px 8px', border: '1px solid #cbd5e1', borderRadius: 4, background: '#fff' }}
            >
              <option value={10}>10</option>
              <option value={15}>15</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </div>
        </div>

        {activity.length === 0 ? (
          <div style={{ padding: '36px 0', textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>
            No execution logs match the selected filter criteria.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e2e8f0', color: '#64748b', fontSize: 11, textTransform: 'uppercase' }}>
                  <th style={{ padding: '8px 10px' }}>ID</th>
                  <th style={{ padding: '8px 10px' }}>Mode</th>
                  <th style={{ padding: '8px 10px' }}>Status</th>
                  <th style={{ padding: '8px 10px' }}>Recipient Email</th>
                  <th style={{ padding: '8px 10px' }}>Subject</th>
                  <th style={{ padding: '8px 10px' }}>Campaign / Job</th>
                  <th style={{ padding: '8px 10px', textAlign: 'center' }}>Att.</th>
                  <th style={{ padding: '8px 10px' }}>Message-ID / Diagnostics</th>
                  <th style={{ padding: '8px 10px', textAlign: 'right' }}>Executed At (UTC)</th>
                </tr>
              </thead>
              <tbody>
                {activity.map(row => (
                  <tr key={row.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '10px', fontSize: 12, color: '#64748b' }}>#{row.id}</td>
                    <td style={{ padding: '10px' }}>{getModeBadge(row.execution_mode)}</td>
                    <td style={{ padding: '10px' }}>{getStatusBadge(row.execution_status)}</td>
                    <td style={{ padding: '10px', fontWeight: 600, color: '#0f172a' }}>{row.recipient_email}</td>
                    <td style={{ padding: '10px', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={row.subject}>
                      {row.subject}
                    </td>
                    <td style={{ padding: '10px', fontSize: 12, color: '#475569' }}>
                      {row.campaign_name || row.reminder_title || <span style={{ color: '#94a3b8' }}>Direct</span>}
                    </td>
                    <td style={{ padding: '10px', textAlign: 'center', fontWeight: 600, color: row.attempt_count > 1 ? '#d97706' : '#64748b' }}>
                      {row.attempt_count}
                    </td>
                    <td style={{ padding: '10px', fontSize: 11, color: '#64748b', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {row.message_id ? (
                        <code style={{ fontSize: 10, background: '#f8fafc', padding: '2px 4px', borderRadius: 3 }} title={row.message_id}>
                          {row.message_id}
                        </code>
                      ) : row.error_message ? (
                        <span style={{ color: '#dc2626' }} title={row.error_message}>{row.error_message}</span>
                      ) : (
                        <span style={{ color: '#cbd5e1' }}>-</span>
                      )}
                    </td>
                    <td style={{ padding: '10px', textAlign: 'right', fontSize: 12, color: '#64748b', whiteSpace: 'nowrap' }}>
                      {row.executed_at ? new Date(row.executed_at).toLocaleString() : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        {totalPages > 1 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 18, borderTop: '1px solid #e2e8f0', paddingTop: 12, fontSize: 13 }}>
            <span style={{ color: '#64748b' }}>
              Page <strong>{page}</strong> of <strong>{totalPages}</strong>
            </span>
            <div style={{ display: 'flex', gap: 6 }}>
              <button
                disabled={page <= 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
                style={{
                  padding: '6px 14px',
                  borderRadius: 6,
                  border: '1px solid #cbd5e1',
                  background: page <= 1 ? '#f8fafc' : '#fff',
                  color: page <= 1 ? '#cbd5e1' : '#0f172a',
                  cursor: page <= 1 ? 'not-allowed' : 'pointer',
                  fontWeight: 600,
                  fontSize: 12
                }}
              >
                Previous
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                style={{
                  padding: '6px 14px',
                  borderRadius: 6,
                  border: '1px solid #cbd5e1',
                  background: page >= totalPages ? '#f8fafc' : '#fff',
                  color: page >= totalPages ? '#cbd5e1' : '#0f172a',
                  cursor: page >= totalPages ? 'not-allowed' : 'pointer',
                  fontWeight: 600,
                  fontSize: 12
                }}
              >
                Next
              </button>
            </div>
          </div>
        )}

      </section>

    </div>
  )
}
