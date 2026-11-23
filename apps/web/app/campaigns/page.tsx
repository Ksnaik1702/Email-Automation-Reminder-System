'use client'

import React, { useState, useEffect } from 'react'

interface EmailTemplate {
  id: number
  template_name: string
  category: string
  subject: string
  body: string
}

interface Employee {
  id: number
  employee_id: string
  full_name: string
  email: string
  company: string
  department: string
  designation: string
  employment_status: string
}

interface CampaignRecipient {
  id: number
  campaign_id: number
  employee_id: number
  recipient_email: string
  status: string
  employee_name?: string
  department?: string
  designation?: string
}

interface Campaign {
  id: number
  campaign_name: string
  description?: string
  category: string
  template_id?: number
  status: string
  scheduled_at?: string
  created_at: string
  updated_at: string
  recipient_count: number
  template_name?: string
}

interface CampaignDetail extends Campaign {
  template?: EmailTemplate
  recipients: CampaignRecipient[]
}

interface CampaignStats {
  total_campaigns: number
  draft_campaigns: number
  ready_campaigns: number
  scheduled_campaigns: number
  completed_campaigns: number
  cancelled_campaigns: number
  total_recipients_targeted: number
}

interface PreviewResult {
  rendered_subject: string
  rendered_html: string
  plain_text_fallback: string
  variables_used: string[]
  missing_variables: string[]
  is_valid: boolean
  validation_error?: string
}

const CATEGORIES = [
  "All",
  "Technical Training",
  "Employee Onboarding",
  "Meeting Invitation",
  "Training Reminder",
  "Performance Review",
  "Webinar Invitation",
  "General Announcement",
  "Task Deadline",
  "Other"
]

const STATUS_LIST = ["ALL", "DRAFT", "READY", "SCHEDULED", "COMPLETED", "CANCELLED"]

export default function CampaignsPage() {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

  // Data states
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [stats, setStats] = useState<CampaignStats | null>(null)
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [successMsg, setSuccessMsg] = useState<string>('')
  const [errorMsg, setErrorMsg] = useState<string>('')

  // Filter states
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('ALL')
  const [categoryFilter, setCategoryFilter] = useState<string>('All')

  // Create Wizard State
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false)
  const [wizardStep, setWizardStep] = useState<number>(1)
  const [formName, setFormName] = useState<string>('')
  const [formDesc, setFormDesc] = useState<string>('')
  const [formCategory, setFormCategory] = useState<string>('General Announcement')
  const [formScheduledAt, setFormScheduledAt] = useState<string>('')
  const [formTemplateId, setFormTemplateId] = useState<number | null>(null)
  const [selectedEmpIds, setSelectedEmpIds] = useState<number[]>([])

  // Recipient targeting filters inside wizard
  const [wizardDeptFilter, setWizardDeptFilter] = useState<string>('All')
  const [wizardEmpSearch, setWizardEmpSearch] = useState<string>('')

  // Preview State (Wizard Step 4 & Standalone Modal)
  const [previewEmpId, setPreviewEmpId] = useState<number | null>(null)
  const [previewResult, setPreviewResult] = useState<PreviewResult | null>(null)
  const [previewLoading, setPreviewLoading] = useState<boolean>(false)
  const [previewMode, setPreviewMode] = useState<'html' | 'text'>('html')

  // Detail / Edit Modal
  const [currentCampaign, setCurrentCampaign] = useState<CampaignDetail | null>(null)
  const [showDetailModal, setShowDetailModal] = useState<boolean>(false)
  const [isEditing, setIsEditing] = useState<boolean>(false)
  const [editName, setEditName] = useState<string>('')
  const [editDesc, setEditDesc] = useState<string>('')
  const [editCategory, setEditCategory] = useState<string>('')
  const [editStatus, setEditStatus] = useState<string>('DRAFT')
  const [editTemplateId, setEditTemplateId] = useState<number | null>(null)
  const [editScheduledAt, setEditScheduledAt] = useState<string>('')

  // Standalone Preview Modal State
  const [standalonePreviewModal, setStandalonePreviewModal] = useState<boolean>(false)
  const [standaloneCampaign, setStandaloneCampaign] = useState<CampaignDetail | null>(null)
  const [standaloneSelectedEmpId, setStandaloneSelectedEmpId] = useState<number | null>(null)

  useEffect(() => {
    loadAllData()
  }, [])

  async function loadAllData() {
    setLoading(true)
    await Promise.all([
      fetchCampaigns(),
      fetchStats(),
      fetchTemplates(),
      fetchEmployees()
    ])
    setLoading(false)
  }

  async function fetchCampaigns() {
    try {
      let url = `${API_URL}/api/campaigns?limit=200`
      if (searchTerm) url += `&search=${encodeURIComponent(searchTerm)}`
      if (statusFilter !== 'ALL') url += `&status=${encodeURIComponent(statusFilter)}`
      if (categoryFilter !== 'All') url += `&category=${encodeURIComponent(categoryFilter)}`

      const res = await fetch(url)
      if (res.ok) {
        const data = await res.json()
        setCampaigns(data.items || [])
      }
    } catch (e: any) {
      console.error('Failed to fetch campaigns', e)
    }
  }

  async function fetchStats() {
    try {
      const res = await fetch(`${API_URL}/api/campaigns/stats`)
      if (res.ok) {
        const data = await res.json()
        setStats(data)
      }
    } catch (e: any) {
      console.error('Failed to fetch stats', e)
    }
  }

  async function fetchTemplates() {
    try {
      const res = await fetch(`${API_URL}/api/templates?limit=100`)
      if (res.ok) {
        const data = await res.json()
        setTemplates(data.items || [])
      }
    } catch (e: any) {
      console.error('Failed to fetch templates', e)
    }
  }

  async function fetchEmployees() {
    try {
      const res = await fetch(`${API_URL}/api/employees?limit=300`)
      if (res.ok) {
        const data = await res.json()
        setEmployees(data.items || [])
      }
    } catch (e: any) {
      console.error('Failed to fetch employees', e)
    }
  }

  function showNotification(msg: string, isErr: boolean = false) {
    if (isErr) {
      setErrorMsg(msg)
      setSuccessMsg('')
      setTimeout(() => setErrorMsg(''), 5000)
    } else {
      setSuccessMsg(msg)
      setErrorMsg('')
      setTimeout(() => setSuccessMsg(''), 5000)
    }
  }

  // --- Wizard Logic ---
  function openCreateWizard() {
    setWizardStep(1)
    setFormName('')
    setFormDesc('')
    setFormCategory('General Announcement')
    setFormScheduledAt('')
    setFormTemplateId(templates.length > 0 ? templates[0].id : null)
    setSelectedEmpIds([])
    setPreviewEmpId(null)
    setPreviewResult(null)
    setShowCreateModal(true)
  }

  function handleSelectAllActive() {
    const activeIds = employees.filter(e => e.employment_status === 'Active').map(e => e.id)
    setSelectedEmpIds(activeIds)
  }

  function handleSelectFiltered() {
    const filteredIds = getFilteredEmployees().map(e => e.id)
    const combined = Array.from(new Set([...selectedEmpIds, ...filteredIds]))
    setSelectedEmpIds(combined)
  }

  function handleDeselectAll() {
    setSelectedEmpIds([])
  }

  function toggleEmployeeSelection(empId: number) {
    setSelectedEmpIds(prev =>
      prev.includes(empId) ? prev.filter(id => id !== empId) : [...prev, empId]
    )
  }

  function getFilteredEmployees() {
    return employees.filter(emp => {
      const matchesDept = wizardDeptFilter === 'All' || emp.department === wizardDeptFilter
      const search = wizardEmpSearch.toLowerCase()
      const matchesSearch =
        !search ||
        emp.full_name.toLowerCase().includes(search) ||
        emp.email.toLowerCase().includes(search) ||
        emp.employee_id.toLowerCase().includes(search) ||
        emp.designation.toLowerCase().includes(search)
      return matchesDept && matchesSearch
    })
  }

  const departmentsList = Array.from(new Set(employees.map(e => e.department))).filter(Boolean)

  async function triggerWizardPreview(empId: number) {
    if (!formTemplateId) return
    const tmpl = templates.find(t => t.id === formTemplateId)
    if (!tmpl) return

    setPreviewLoading(true)
    setPreviewEmpId(empId)
    try {
      const res = await fetch(`${API_URL}/api/templates/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: tmpl.subject,
          body: tmpl.body,
          employee_id: empId
        })
      })

      if (res.ok) {
        const data = await res.json()
        setPreviewResult(data)
      } else {
        const err = await res.json()
        showNotification(err.detail || 'Preview generation failed', true)
      }
    } catch (e: any) {
      showNotification(e.message, true)
    } finally {
      setPreviewLoading(false)
    }
  }

  async function handleSaveCampaign(statusToSave: 'DRAFT' | 'READY') {
    if (!formName.trim()) {
      showNotification('Campaign name is required', true)
      return
    }

    try {
      const payload = {
        campaign_name: formName.trim(),
        description: formDesc.trim() || undefined,
        category: formCategory,
        template_id: formTemplateId || undefined,
        status: statusToSave,
        scheduled_at: formScheduledAt ? new Date(formScheduledAt).toISOString() : undefined,
        employee_ids: selectedEmpIds
      }

      const res = await fetch(`${API_URL}/api/campaigns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (res.ok) {
        showNotification(`Campaign "${formName}" created as ${statusToSave} with ${selectedEmpIds.length} recipients.`)
        setShowCreateModal(false)
        await loadAllData()
      } else {
        const err = await res.json()
        showNotification(err.detail || 'Failed to create campaign', true)
      }
    } catch (e: any) {
      showNotification(e.message, true)
    }
  }

  // --- Campaign Details & Edit ---
  async function openCampaignDetail(campId: number) {
    try {
      const res = await fetch(`${API_URL}/api/campaigns/${campId}`)
      if (res.ok) {
        const data: CampaignDetail = await res.json()
        setCurrentCampaign(data)
        setEditName(data.campaign_name)
        setEditDesc(data.description || '')
        setEditCategory(data.category)
        setEditStatus(data.status)
        setEditTemplateId(data.template_id || null)
        setEditScheduledAt(data.scheduled_at ? data.scheduled_at.slice(0, 16) : '')
        setIsEditing(false)
        setShowDetailModal(true)
      } else {
        showNotification('Failed to fetch campaign details', true)
      }
    } catch (e: any) {
      showNotification(e.message, true)
    }
  }

  async function handleUpdateCampaign() {
    if (!currentCampaign) return
    try {
      const payload = {
        campaign_name: editName.trim(),
        description: editDesc.trim() || undefined,
        category: editCategory,
        status: editStatus,
        template_id: editTemplateId || undefined,
        scheduled_at: editScheduledAt ? new Date(editScheduledAt).toISOString() : undefined
      }

      const res = await fetch(`${API_URL}/api/campaigns/${currentCampaign.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (res.ok) {
        showNotification('Campaign updated successfully')
        setIsEditing(false)
        await openCampaignDetail(currentCampaign.id)
        await loadAllData()
      } else {
        const err = await res.json()
        showNotification(err.detail || 'Failed to update campaign', true)
      }
    } catch (e: any) {
      showNotification(e.message, true)
    }
  }

  async function handleDeleteCampaign(campId: number, campName: string) {
    if (!confirm(`Are you sure you want to delete campaign "${campName}"? This will remove all associated recipient targeting.`)) {
      return
    }

    try {
      const res = await fetch(`${API_URL}/api/campaigns/${campId}`, {
        method: 'DELETE'
      })

      if (res.ok) {
        showNotification(`Campaign "${campName}" deleted successfully.`)
        if (showDetailModal) setShowDetailModal(false)
        await loadAllData()
      } else {
        const err = await res.json()
        showNotification(err.detail || 'Failed to delete campaign', true)
      }
    } catch (e: any) {
      showNotification(e.message, true)
    }
  }

  async function handleRemoveRecipient(campId: number, empId: number) {
    try {
      const res = await fetch(`${API_URL}/api/campaigns/${campId}/recipients/${empId}`, {
        method: 'DELETE'
      })
      if (res.ok) {
        showNotification('Recipient removed from campaign')
        await openCampaignDetail(campId)
        await loadAllData()
      } else {
        const err = await res.json()
        showNotification(err.detail || 'Failed to remove recipient', true)
      }
    } catch (e: any) {
      showNotification(e.message, true)
    }
  }

  // --- Standalone Personalized Preview ---
  async function openStandalonePreview(campId: number) {
    try {
      const res = await fetch(`${API_URL}/api/campaigns/${campId}`)
      if (res.ok) {
        const data: CampaignDetail = await res.json()
        setStandaloneCampaign(data)
        setStandalonePreviewModal(true)
        if (data.recipients.length > 0) {
          const firstEmpId = data.recipients[0].employee_id
          setStandaloneSelectedEmpId(firstEmpId)
          loadStandalonePreview(campId, firstEmpId)
        } else {
          setPreviewResult(null)
        }
      }
    } catch (e: any) {
      showNotification(e.message, true)
    }
  }

  async function loadStandalonePreview(campId: number, empId: number) {
    setPreviewLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/campaigns/${campId}/preview/${empId}`)
      if (res.ok) {
        const data = await res.json()
        setPreviewResult(data)
      } else {
        const err = await res.json()
        showNotification(err.detail || 'Preview generation failed', true)
      }
    } catch (e: any) {
      showNotification(e.message, true)
    } finally {
      setPreviewLoading(false)
    }
  }

  function getStatusBadgeStyle(st: string) {
    switch (st) {
      case 'READY':
        return { bg: '#ecfdf5', text: '#065f46', border: '#a7f3d0' }
      case 'DRAFT':
        return { bg: '#f1f5f9', text: '#475569', border: '#cbd5e1' }
      case 'SCHEDULED':
        return { bg: '#fffbeb', text: '#92400e', border: '#fde68a' }
      case 'COMPLETED':
        return { bg: '#eff6ff', text: '#1e40af', border: '#bfdbfe' }
      case 'CANCELLED':
        return { bg: '#fef2f2', text: '#991b1b', border: '#fecaca' }
      default:
        return { bg: '#f8fafc', text: '#334155', border: '#e2e8f0' }
    }
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '32px 20px', fontFamily: 'system-ui, -apple-system, sans-serif', color: '#0f172a' }}>
      
      {/* Top Breadcrumb Navigation */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28, borderBottom: '1px solid #e2e8f0', paddingBottom: 20 }}>
        <div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 4 }}>
            <a href="/" style={{ color: '#64748b', textDecoration: 'none', fontSize: 13 }}>Home</a>
            <span style={{ color: '#cbd5e1' }}>/</span>
            <a href="/employees" style={{ color: '#64748b', textDecoration: 'none', fontSize: 13 }}>Workforce</a>
            <span style={{ color: '#cbd5e1' }}>/</span>
            <a href="/templates" style={{ color: '#64748b', textDecoration: 'none', fontSize: 13 }}>Templates</a>
            <span style={{ color: '#cbd5e1' }}>/</span>
            <span style={{ fontSize: 13, fontWeight: 600 }}>Campaigns</span>
          </div>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0, color: '#0f172a' }}>Email Campaign Studio</h1>
          <p style={{ color: '#64748b', margin: '4px 0 0 0', fontSize: 14 }}>
            Create multi-recipient notification campaigns, target employee cohorts, and preview personalized emails
          </p>
        </div>

        <button
          onClick={openCreateWizard}
          style={{ backgroundColor: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, padding: '10px 18px', fontSize: 13, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}
        >
          <span>+</span> Create New Campaign
        </button>
      </header>

      {/* Notifications */}
      {successMsg && (
        <div style={{ padding: '12px 16px', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 6, marginBottom: 20, color: '#166534', fontSize: 13 }}>
          {successMsg}
        </div>
      )}
      {errorMsg && (
        <div style={{ padding: '12px 16px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 6, marginBottom: 20, color: '#991b1b', fontSize: 13 }}>
          {errorMsg}
        </div>
      )}

      {/* Metric Cards Bar */}
      {stats && (
        <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 14, marginBottom: 24 }}>
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '14px 18px' }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>Total Campaigns</span>
            <div style={{ fontSize: 26, fontWeight: 700, color: '#0f172a', marginTop: 2 }}>{stats.total_campaigns}</div>
          </div>
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '14px 18px' }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: '#059669', textTransform: 'uppercase' }}>Ready for Dispatch</span>
            <div style={{ fontSize: 26, fontWeight: 700, color: '#059669', marginTop: 2 }}>{stats.ready_campaigns}</div>
          </div>
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '14px 18px' }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: '#475569', textTransform: 'uppercase' }}>Draft Campaigns</span>
            <div style={{ fontSize: 26, fontWeight: 700, color: '#475569', marginTop: 2 }}>{stats.draft_campaigns}</div>
          </div>
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '14px 18px' }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: '#d97706', textTransform: 'uppercase' }}>Scheduled</span>
            <div style={{ fontSize: 26, fontWeight: 700, color: '#d97706', marginTop: 2 }}>{stats.scheduled_campaigns}</div>
          </div>
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '14px 18px' }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: '#2563eb', textTransform: 'uppercase' }}>Targeted Recipients</span>
            <div style={{ fontSize: 26, fontWeight: 700, color: '#2563eb', marginTop: 2 }}>{stats.total_recipients_targeted}</div>
          </div>
        </section>
      )}

      {/* Filter and Search Bar */}
      <section style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          type="text"
          placeholder="Search campaigns by title or description..."
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') fetchCampaigns() }}
          style={{ flex: '1 1 240px', padding: '9px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13 }}
        />

        {/* Status Dropdown */}
        <select
          value={statusFilter}
          onChange={e => { setStatusFilter(e.target.value); }}
          style={{ padding: '9px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13, background: '#fff' }}
        >
          {STATUS_LIST.map(st => (
            <option key={st} value={st}>Status: {st}</option>
          ))}
        </select>

        {/* Category Dropdown */}
        <select
          value={categoryFilter}
          onChange={e => { setCategoryFilter(e.target.value); }}
          style={{ padding: '9px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13, background: '#fff' }}
        >
          {CATEGORIES.map(cat => (
            <option key={cat} value={cat}>Category: {cat}</option>
          ))}
        </select>

        <button
          onClick={fetchCampaigns}
          style={{ backgroundColor: '#f1f5f9', border: '1px solid #cbd5e1', borderRadius: 6, padding: '9px 14px', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
        >
          Apply Filters
        </button>
      </section>

      {/* Campaign List Table */}
      <section style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 13 }}>
          <thead style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
            <tr>
              <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569' }}>Campaign</th>
              <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569' }}>Category</th>
              <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569' }}>Template</th>
              <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569' }}>Recipients</th>
              <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569' }}>Status</th>
              <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569' }}>Scheduled At</th>
              <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ padding: '36px', textAlign: 'center', color: '#64748b' }}>
                  Loading campaigns...
                </td>
              </tr>
            ) : campaigns.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: '48px', textAlign: 'center', color: '#64748b' }}>
                  <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 6 }}>No campaigns found</div>
                  <div style={{ fontSize: 13 }}>Create your first email campaign to begin targeting recipients.</div>
                  <button
                    onClick={openCreateWizard}
                    style={{ marginTop: 16, backgroundColor: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, padding: '8px 16px', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
                  >
                    + Create Campaign
                  </button>
                </td>
              </tr>
            ) : (
              campaigns.map(camp => {
                const badge = getStatusBadgeStyle(camp.status)
                return (
                  <tr key={camp.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ fontWeight: 600, color: '#0f172a' }}>{camp.campaign_name}</div>
                      {camp.description && (
                        <div style={{ color: '#64748b', fontSize: 12, marginTop: 2, maxWidth: 280, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {camp.description}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <span style={{ background: '#f1f5f9', padding: '3px 8px', borderRadius: 4, fontSize: 12, color: '#475569' }}>
                        {camp.category}
                      </span>
                    </td>
                    <td style={{ padding: '14px 16px', color: '#334155' }}>
                      {camp.template_name ? (
                        <span style={{ color: '#2563eb', fontWeight: 500 }}>{camp.template_name}</span>
                      ) : (
                        <span style={{ color: '#94a3b8', fontStyle: 'italic' }}>None</span>
                      )}
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: '#f8fafc', border: '1px solid #e2e8f0', padding: '3px 10px', borderRadius: 12, fontSize: 12, fontWeight: 600, color: '#0f172a' }}>
                        <span>👥</span> {camp.recipient_count}
                      </span>
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <span style={{
                        backgroundColor: badge.bg,
                        color: badge.text,
                        border: `1px solid ${badge.border}`,
                        padding: '3px 8px',
                        borderRadius: 12,
                        fontSize: 11,
                        fontWeight: 700,
                        textTransform: 'uppercase'
                      }}>
                        {camp.status}
                      </span>
                    </td>
                    <td style={{ padding: '14px 16px', color: '#64748b', fontSize: 12 }}>
                      {camp.scheduled_at ? new Date(camp.scheduled_at).toLocaleString() : 'Immediate / Unscheduled'}
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: 8 }}>
                        <button
                          onClick={() => openStandalonePreview(camp.id)}
                          title="Preview Personalized Email"
                          style={{ background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: 4, padding: '5px 10px', fontSize: 12, cursor: 'pointer', color: '#2563eb', fontWeight: 600 }}
                        >
                          👁️ Preview
                        </button>
                        <button
                          onClick={() => openCampaignDetail(camp.id)}
                          title="View / Edit Campaign"
                          style={{ background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: 4, padding: '5px 10px', fontSize: 12, cursor: 'pointer', color: '#334155' }}
                        >
                          Manage
                        </button>
                        <button
                          onClick={() => handleDeleteCampaign(camp.id, camp.campaign_name)}
                          title="Delete Campaign"
                          style={{ background: '#fff', border: '1px solid #fecaca', borderRadius: 4, padding: '5px 10px', fontSize: 12, cursor: 'pointer', color: '#dc2626' }}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </section>

      {/* ----------------- CREATE CAMPAIGN 5-STEP WIZARD MODAL ----------------- */}
      {showCreateModal && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15,23,42,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50, padding: 20 }}>
          <div style={{ background: '#fff', borderRadius: 10, width: '100%', maxWidth: 840, maxHeight: '90vh', display: 'flex', flexDirection: 'column', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}>
            
            {/* Modal Header */}
            <div style={{ padding: '18px 24px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>Create Email Campaign</h2>
                <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>
                  Step {wizardStep} of 5: {
                    wizardStep === 1 ? 'Campaign Details' :
                    wizardStep === 2 ? 'Select Email Template' :
                    wizardStep === 3 ? 'Target Recipients' :
                    wizardStep === 4 ? 'Personalized Preview' : 'Review & Confirm'
                  }
                </div>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', color: '#64748b' }}
              >
                &times;
              </button>
            </div>

            {/* Stepper Progress Bar */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', borderBottom: '1px solid #e2e8f0', background: '#f8fafc' }}>
              {[
                { step: 1, label: '1. Setup' },
                { step: 2, label: '2. Template' },
                { step: 3, label: '3. Recipients' },
                { step: 4, label: '4. Preview' },
                { step: 5, label: '5. Review' }
              ].map(s => (
                <div
                  key={s.step}
                  onClick={() => { if (s.step < wizardStep || (s.step === 2 && formName.trim())) setWizardStep(s.step) }}
                  style={{
                    padding: '10px 8px',
                    textAlign: 'center',
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: 'pointer',
                    color: wizardStep === s.step ? '#2563eb' : (wizardStep > s.step ? '#059669' : '#94a3b8'),
                    borderBottom: wizardStep === s.step ? '2px solid #2563eb' : 'none',
                    background: wizardStep === s.step ? '#fff' : 'transparent'
                  }}
                >
                  {s.label} {wizardStep > s.step && '✓'}
                </div>
              ))}
            </div>

            {/* Modal Body */}
            <div style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>
              
              {/* STEP 1: Basic Campaign Details */}
              {wizardStep === 1 && (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                      Campaign Title <span style={{ color: '#dc2626' }}>*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Q4 Company-wide Security Awareness Training"
                      value={formName}
                      onChange={e => setFormName(e.target.value)}
                      style={{ width: '100%', padding: '9px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13 }}
                    />
                  </div>

                  <div style={{ marginBottom: 16 }}>
                    <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                      Description (Optional)
                    </label>
                    <textarea
                      rows={2}
                      placeholder="Operational purpose of this email campaign..."
                      value={formDesc}
                      onChange={e => setFormDesc(e.target.value)}
                      style={{ width: '100%', padding: '9px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13 }}
                    />
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                    <div>
                      <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                        Category
                      </label>
                      <select
                        value={formCategory}
                        onChange={e => setFormCategory(e.target.value)}
                        style={{ width: '100%', padding: '9px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13, background: '#fff' }}
                      >
                        {CATEGORIES.filter(c => c !== 'All').map(c => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                        Scheduled Launch Time (Optional)
                      </label>
                      <input
                        type="datetime-local"
                        value={formScheduledAt}
                        onChange={e => setFormScheduledAt(e.target.value)}
                        style={{ width: '100%', padding: '8px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13 }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 2: Template Selection */}
              {wizardStep === 2 && (
                <div>
                  <p style={{ margin: '0 0 16px 0', fontSize: 13, color: '#64748b' }}>
                    Select an email template from your centralized template library to power this campaign.
                  </p>

                  {templates.length === 0 ? (
                    <div style={{ padding: 24, textAlign: 'center', background: '#f8fafc', borderRadius: 6 }}>
                      <p style={{ margin: 0, color: '#64748b' }}>No templates available. Please create a template in the Template Studio first.</p>
                      <a href="/templates" style={{ display: 'inline-block', marginTop: 10, color: '#2563eb', fontWeight: 600 }}>Go to Template Studio &rarr;</a>
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gap: 12, maxHeight: 380, overflowY: 'auto' }}>
                      {templates.map(tmpl => {
                        const isSelected = formTemplateId === tmpl.id
                        return (
                          <div
                            key={tmpl.id}
                            onClick={() => setFormTemplateId(tmpl.id)}
                            style={{
                              padding: '14px 18px',
                              border: isSelected ? '2px solid #2563eb' : '1px solid #e2e8f0',
                              background: isSelected ? '#eff6ff' : '#fff',
                              borderRadius: 8,
                              cursor: 'pointer',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center'
                            }}
                          >
                            <div>
                              <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                                <span style={{ fontWeight: 600, fontSize: 14, color: isSelected ? '#1e40af' : '#0f172a' }}>
                                  {tmpl.template_name}
                                </span>
                                <span style={{ background: '#e2e8f0', padding: '2px 6px', borderRadius: 4, fontSize: 11, color: '#475569' }}>
                                  {tmpl.category}
                                </span>
                              </div>
                              <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                                Subject: <span style={{ fontFamily: 'monospace' }}>{tmpl.subject}</span>
                              </div>
                            </div>
                            <input
                              type="radio"
                              name="selected_template"
                              checked={isSelected}
                              onChange={() => setFormTemplateId(tmpl.id)}
                              style={{ width: 18, height: 18, cursor: 'pointer' }}
                            />
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* STEP 3: Recipient Targeting */}
              {wizardStep === 3 && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <div>
                      <span style={{ fontSize: 13, fontWeight: 600 }}>Target Employee Recipients</span>
                      <span style={{ marginLeft: 8, background: '#eff6ff', color: '#1e40af', padding: '2px 8px', borderRadius: 12, fontSize: 12, fontWeight: 700 }}>
                        {selectedEmpIds.length} Selected
                      </span>
                    </div>

                    <div style={{ display: 'flex', gap: 8 }}>
                      <button
                        onClick={handleSelectAllActive}
                        style={{ background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: 4, padding: '4px 10px', fontSize: 12, fontWeight: 500, cursor: 'pointer' }}
                      >
                        Select All Active ({employees.filter(e => e.employment_status === 'Active').length})
                      </button>
                      <button
                        onClick={handleSelectFiltered}
                        style={{ background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: 4, padding: '4px 10px', fontSize: 12, fontWeight: 500, cursor: 'pointer' }}
                      >
                        Select Filtered
                      </button>
                      <button
                        onClick={handleDeselectAll}
                        style={{ background: '#fff', border: '1px solid #fecaca', borderRadius: 4, padding: '4px 10px', fontSize: 12, color: '#dc2626', cursor: 'pointer' }}
                      >
                        Deselect All
                      </button>
                    </div>
                  </div>

                  {/* Recipient Filter Controls */}
                  <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
                    <input
                      type="text"
                      placeholder="Search employees by name, email, or designation..."
                      value={wizardEmpSearch}
                      onChange={e => setWizardEmpSearch(e.target.value)}
                      style={{ flex: 1, padding: '7px 10px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 12 }}
                    />
                    <select
                      value={wizardDeptFilter}
                      onChange={e => setWizardDeptFilter(e.target.value)}
                      style={{ padding: '7px 10px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 12, background: '#fff' }}
                    >
                      <option value="All">All Departments</option>
                      {departmentsList.map(d => (
                        <option key={d} value={d}>{d}</option>
                      ))}
                    </select>
                  </div>

                  {/* Employee Table */}
                  <div style={{ maxHeight: 320, overflowY: 'auto', border: '1px solid #e2e8f0', borderRadius: 6 }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                      <thead style={{ background: '#f8fafc', position: 'sticky', top: 0, borderBottom: '1px solid #e2e8f0' }}>
                        <tr>
                          <th style={{ padding: '8px 12px', width: 30 }}></th>
                          <th style={{ padding: '8px 12px', textAlign: 'left', color: '#475569' }}>Name</th>
                          <th style={{ padding: '8px 12px', textAlign: 'left', color: '#475569' }}>Email</th>
                          <th style={{ padding: '8px 12px', textAlign: 'left', color: '#475569' }}>Department</th>
                          <th style={{ padding: '8px 12px', textAlign: 'left', color: '#475569' }}>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {getFilteredEmployees().map(emp => {
                          const isChecked = selectedEmpIds.includes(emp.id)
                          return (
                            <tr
                              key={emp.id}
                              onClick={() => toggleEmployeeSelection(emp.id)}
                              style={{
                                borderBottom: '1px solid #f1f5f9',
                                background: isChecked ? '#f0fdf4' : '#fff',
                                cursor: 'pointer'
                              }}
                            >
                              <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                                <input
                                  type="checkbox"
                                  checked={isChecked}
                                  onChange={() => {}}
                                  style={{ cursor: 'pointer' }}
                                />
                              </td>
                              <td style={{ padding: '8px 12px', fontWeight: 600 }}>{emp.full_name}</td>
                              <td style={{ padding: '8px 12px', color: '#64748b' }}>{emp.email}</td>
                              <td style={{ padding: '8px 12px' }}>{emp.department}</td>
                              <td style={{ padding: '8px 12px' }}>
                                <span style={{
                                  fontSize: 10,
                                  fontWeight: 700,
                                  padding: '2px 6px',
                                  borderRadius: 8,
                                  background: emp.employment_status === 'Active' ? '#dcfce7' : '#fee2e2',
                                  color: emp.employment_status === 'Active' ? '#166534' : '#991b1b'
                                }}>
                                  {emp.employment_status}
                                </span>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* STEP 4: Personalized Preview */}
              {wizardStep === 4 && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                    <div>
                      <span style={{ fontSize: 13, fontWeight: 600 }}>Select Recipient to Preview: </span>
                      <select
                        value={previewEmpId || ''}
                        onChange={e => {
                          const id = Number(e.target.value)
                          triggerWizardPreview(id)
                        }}
                        style={{ marginLeft: 8, padding: '6px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 12, background: '#fff' }}
                      >
                        {selectedEmpIds.length === 0 ? (
                          <option value="">No recipients selected</option>
                        ) : (
                          employees
                            .filter(e => selectedEmpIds.includes(e.id))
                            .map(e => (
                              <option key={e.id} value={e.id}>{e.full_name} ({e.email}) - {e.department}</option>
                            ))
                        )}
                      </select>
                    </div>

                    <div style={{ display: 'inline-flex', background: '#f1f5f9', borderRadius: 6, padding: 2 }}>
                      <button
                        onClick={() => setPreviewMode('html')}
                        style={{
                          background: previewMode === 'html' ? '#fff' : 'transparent',
                          border: 'none',
                          borderRadius: 4,
                          padding: '4px 10px',
                          fontSize: 12,
                          fontWeight: 600,
                          cursor: 'pointer'
                        }}
                      >
                        Rendered HTML
                      </button>
                      <button
                        onClick={() => setPreviewMode('text')}
                        style={{
                          background: previewMode === 'text' ? '#fff' : 'transparent',
                          border: 'none',
                          borderRadius: 4,
                          padding: '4px 10px',
                          fontSize: 12,
                          fontWeight: 600,
                          cursor: 'pointer'
                        }}
                      >
                        Plain Text Fallback
                      </button>
                    </div>
                  </div>

                  {previewLoading ? (
                    <div style={{ padding: 40, textAlign: 'center', color: '#64748b' }}>Rendering personalized email preview...</div>
                  ) : previewResult ? (
                    <div style={{ border: '1px solid #e2e8f0', borderRadius: 8, overflow: 'hidden' }}>
                      <div style={{ padding: '10px 16px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', fontSize: 13 }}>
                        <span style={{ fontWeight: 600, color: '#475569' }}>Subject: </span>
                        <span style={{ fontWeight: 700, color: '#0f172a' }}>{previewResult.rendered_subject}</span>
                      </div>
                      
                      {previewMode === 'html' ? (
                        <div
                          style={{ padding: 18, background: '#fff', minHeight: 180, fontSize: 13 }}
                          dangerouslySetInnerHTML={{ __html: previewResult.rendered_html }}
                        />
                      ) : (
                        <pre style={{ padding: 18, background: '#fafafa', margin: 0, minHeight: 180, fontSize: 12, whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                          {previewResult.plain_text_fallback}
                        </pre>
                      )}

                      <div style={{ padding: '8px 16px', background: '#f8fafc', borderTop: '1px solid #e2e8f0', fontSize: 11, color: '#64748b', display: 'flex', gap: 14 }}>
                        <span>Variables Resolved: <strong>{previewResult.variables_used.join(', ') || 'None'}</strong></span>
                        {previewResult.missing_variables.length > 0 && (
                          <span style={{ color: '#dc2626' }}>Missing: <strong>{previewResult.missing_variables.join(', ')}</strong></span>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div style={{ padding: 40, textAlign: 'center', color: '#64748b' }}>
                      Please select a recipient above to render the email preview.
                    </div>
                  )}
                </div>
              )}

              {/* STEP 5: Review & Save */}
              {wizardStep === 5 && (
                <div>
                  <h3 style={{ fontSize: 15, fontWeight: 700, margin: '0 0 14px 0' }}>Campaign Summary</h3>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
                    <div style={{ background: '#f8fafc', padding: 16, borderRadius: 8, border: '1px solid #e2e8f0' }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>Campaign Name</div>
                      <div style={{ fontSize: 15, fontWeight: 700, color: '#0f172a', marginTop: 2 }}>{formName}</div>

                      <div style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', marginTop: 12 }}>Category</div>
                      <div style={{ fontSize: 13, color: '#334155', marginTop: 2 }}>{formCategory}</div>

                      <div style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', marginTop: 12 }}>Scheduled Launch</div>
                      <div style={{ fontSize: 13, color: '#334155', marginTop: 2 }}>
                        {formScheduledAt ? new Date(formScheduledAt).toLocaleString() : 'Immediate / Unscheduled'}
                      </div>
                    </div>

                    <div style={{ background: '#f8fafc', padding: 16, borderRadius: 8, border: '1px solid #e2e8f0' }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>Selected Template</div>
                      <div style={{ fontSize: 14, fontWeight: 700, color: '#2563eb', marginTop: 2 }}>
                        {templates.find(t => t.id === formTemplateId)?.template_name || 'None'}
                      </div>

                      <div style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', marginTop: 12 }}>Total Targeted Recipients</div>
                      <div style={{ fontSize: 24, fontWeight: 700, color: '#059669', marginTop: 2 }}>
                        {selectedEmpIds.length} Employees
                      </div>
                    </div>
                  </div>

                  <p style={{ fontSize: 13, color: '#64748b' }}>
                    You can save this campaign as a <strong>DRAFT</strong> for future editing, or mark it as <strong>READY</strong> for scheduled automated delivery.
                  </p>
                </div>
              )}

            </div>

            {/* Modal Footer Controls */}
            <div style={{ padding: '16px 24px', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                {wizardStep > 1 && (
                  <button
                    onClick={() => setWizardStep(prev => prev - 1)}
                    style={{ background: '#f1f5f9', border: '1px solid #cbd5e1', borderRadius: 6, padding: '8px 16px', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
                  >
                    &larr; Back
                  </button>
                )}
              </div>

              <div style={{ display: 'flex', gap: 10 }}>
                {wizardStep < 5 ? (
                  <button
                    onClick={() => {
                      if (wizardStep === 1 && !formName.trim()) {
                        showNotification('Campaign title is required', true)
                        return
                      }
                      if (wizardStep === 3 && selectedEmpIds.length > 0 && !previewEmpId) {
                        triggerWizardPreview(selectedEmpIds[0])
                      }
                      setWizardStep(prev => prev + 1)
                    }}
                    style={{ backgroundColor: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, padding: '8px 18px', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
                  >
                    Next Step &rarr;
                  </button>
                ) : (
                  <>
                    <button
                      onClick={() => handleSaveCampaign('DRAFT')}
                      style={{ background: '#f1f5f9', color: '#334155', border: '1px solid #cbd5e1', borderRadius: 6, padding: '8px 16px', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
                    >
                      Save as Draft
                    </button>
                    <button
                      onClick={() => handleSaveCampaign('READY')}
                      style={{ backgroundColor: '#059669', color: '#fff', border: 'none', borderRadius: 6, padding: '8px 20px', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}
                    >
                      ✓ Mark as Ready
                    </button>
                  </>
                )}
              </div>
            </div>

          </div>
        </div>
      )}

      {/* ----------------- CAMPAIGN MANAGE / DETAIL MODAL ----------------- */}
      {showDetailModal && currentCampaign && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15,23,42,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50, padding: 20 }}>
          <div style={{ background: '#fff', borderRadius: 10, width: '100%', maxWidth: 780, maxHeight: '88vh', display: 'flex', flexDirection: 'column', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}>
            
            <div style={{ padding: '18px 24px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>
                  {isEditing ? 'Edit Campaign' : currentCampaign.campaign_name}
                </h2>
                <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>
                  Status: <strong>{currentCampaign.status}</strong> | Recipients: <strong>{currentCampaign.recipients.length}</strong>
                </div>
              </div>
              <button
                onClick={() => setShowDetailModal(false)}
                style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', color: '#64748b' }}
              >
                &times;
              </button>
            </div>

            <div style={{ padding: '20px 24px', overflowY: 'auto', flex: 1 }}>
              {isEditing ? (
                <div>
                  <div style={{ marginBottom: 14 }}>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Campaign Name</label>
                    <input
                      type="text"
                      value={editName}
                      onChange={e => setEditName(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13 }}
                    />
                  </div>

                  <div style={{ marginBottom: 14 }}>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Description</label>
                    <textarea
                      rows={2}
                      value={editDesc}
                      onChange={e => setEditDesc(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13 }}
                    />
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
                    <div>
                      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Status</label>
                      <select
                        value={editStatus}
                        onChange={e => setEditStatus(e.target.value)}
                        style={{ width: '100%', padding: '8px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13, background: '#fff' }}
                      >
                        {STATUS_LIST.filter(s => s !== 'ALL').map(s => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Category</label>
                      <select
                        value={editCategory}
                        onChange={e => setEditCategory(e.target.value)}
                        style={{ width: '100%', padding: '8px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13, background: '#fff' }}
                      >
                        {CATEGORIES.filter(c => c !== 'All').map(c => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
                    <div>
                      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Template</label>
                      <select
                        value={editTemplateId || ''}
                        onChange={e => setEditTemplateId(e.target.value ? Number(e.target.value) : null)}
                        style={{ width: '100%', padding: '8px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13, background: '#fff' }}
                      >
                        <option value="">None</option>
                        {templates.map(t => (
                          <option key={t.id} value={t.id}>{t.template_name} ({t.category})</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Scheduled At</label>
                      <input
                        type="datetime-local"
                        value={editScheduledAt}
                        onChange={e => setEditScheduledAt(e.target.value)}
                        style={{ width: '100%', padding: '8px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13 }}
                      />
                    </div>
                  </div>
                </div>
              ) : (
                <div>
                  {currentCampaign.description && (
                    <div style={{ fontSize: 13, color: '#475569', marginBottom: 16 }}>
                      {currentCampaign.description}
                    </div>
                  )}

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 20 }}>
                    <div style={{ background: '#f8fafc', padding: 12, borderRadius: 6 }}>
                      <span style={{ fontSize: 11, color: '#64748b' }}>Category:</span>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>{currentCampaign.category}</div>
                    </div>
                    <div style={{ background: '#f8fafc', padding: 12, borderRadius: 6 }}>
                      <span style={{ fontSize: 11, color: '#64748b' }}>Template:</span>
                      <div style={{ fontWeight: 600, fontSize: 13, color: '#2563eb' }}>
                        {currentCampaign.template ? currentCampaign.template.template_name : 'None'}
                      </div>
                    </div>
                    <div style={{ background: '#f8fafc', padding: 12, borderRadius: 6 }}>
                      <span style={{ fontSize: 11, color: '#64748b' }}>Scheduled Launch:</span>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>
                        {currentCampaign.scheduled_at ? new Date(currentCampaign.scheduled_at).toLocaleString() : 'Unscheduled'}
                      </div>
                    </div>
                  </div>

                  {/* Recipients List */}
                  <h4 style={{ fontSize: 13, fontWeight: 700, margin: '0 0 10px 0', color: '#0f172a' }}>
                    Targeted Recipients ({currentCampaign.recipients.length})
                  </h4>

                  <div style={{ maxHeight: 240, overflowY: 'auto', border: '1px solid #e2e8f0', borderRadius: 6 }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                      <thead style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                        <tr>
                          <th style={{ padding: '8px 12px', textAlign: 'left', color: '#475569' }}>Name</th>
                          <th style={{ padding: '8px 12px', textAlign: 'left', color: '#475569' }}>Email</th>
                          <th style={{ padding: '8px 12px', textAlign: 'left', color: '#475569' }}>Department</th>
                          <th style={{ padding: '8px 12px', textAlign: 'right', color: '#475569' }}>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {currentCampaign.recipients.map(r => (
                          <tr key={r.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                            <td style={{ padding: '8px 12px', fontWeight: 600 }}>{r.employee_name || 'N/A'}</td>
                            <td style={{ padding: '8px 12px', color: '#64748b' }}>{r.recipient_email}</td>
                            <td style={{ padding: '8px 12px' }}>{r.department || 'N/A'}</td>
                            <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                              <button
                                onClick={() => handleRemoveRecipient(currentCampaign.id, r.employee_id)}
                                style={{ background: 'none', border: 'none', color: '#dc2626', fontSize: 11, cursor: 'pointer', fontWeight: 600 }}
                              >
                                Remove
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>

            <div style={{ padding: '16px 24px', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between' }}>
              <div>
                <button
                  onClick={() => handleDeleteCampaign(currentCampaign.id, currentCampaign.campaign_name)}
                  style={{ background: '#fff', border: '1px solid #fecaca', borderRadius: 6, padding: '8px 14px', fontSize: 12, color: '#dc2626', cursor: 'pointer' }}
                >
                  Delete Campaign
                </button>
              </div>

              <div style={{ display: 'flex', gap: 10 }}>
                {isEditing ? (
                  <>
                    <button
                      onClick={() => setIsEditing(false)}
                      style={{ background: '#f1f5f9', border: '1px solid #cbd5e1', borderRadius: 6, padding: '8px 14px', fontSize: 12, cursor: 'pointer' }}
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleUpdateCampaign}
                      style={{ backgroundColor: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, padding: '8px 16px', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
                    >
                      Save Changes
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => {
                        setShowDetailModal(false)
                        openStandalonePreview(currentCampaign.id)
                      }}
                      style={{ background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: 6, padding: '8px 14px', fontSize: 12, color: '#2563eb', fontWeight: 600, cursor: 'pointer' }}
                    >
                      👁️ Preview Output
                    </button>
                    <button
                      onClick={() => setIsEditing(true)}
                      style={{ backgroundColor: '#0f172a', color: '#fff', border: 'none', borderRadius: 6, padding: '8px 16px', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
                    >
                      Edit Campaign
                    </button>
                  </>
                )}
              </div>
            </div>

          </div>
        </div>
      )}

      {/* ----------------- STANDALONE PERSONALIZED PREVIEW MODAL ----------------- */}
      {standalonePreviewModal && standaloneCampaign && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15,23,42,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 60, padding: 20 }}>
          <div style={{ background: '#fff', borderRadius: 10, width: '100%', maxWidth: 780, maxHeight: '88vh', display: 'flex', flexDirection: 'column', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}>
            
            <div style={{ padding: '18px 24px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>
                  Personalized Email Preview
                </h2>
                <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>
                  Campaign: <strong>{standaloneCampaign.campaign_name}</strong> | Template: <strong>{standaloneCampaign.template?.template_name || 'N/A'}</strong>
                </div>
              </div>
              <button
                onClick={() => setStandalonePreviewModal(false)}
                style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', color: '#64748b' }}
              >
                &times;
              </button>
            </div>

            <div style={{ padding: '20px 24px', overflowY: 'auto', flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                <div>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>Recipient: </span>
                  <select
                    value={standaloneSelectedEmpId || ''}
                    onChange={e => {
                      const id = Number(e.target.value)
                      setStandaloneSelectedEmpId(id)
                      loadStandalonePreview(standaloneCampaign.id, id)
                    }}
                    style={{ marginLeft: 8, padding: '6px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 12, background: '#fff' }}
                  >
                    {standaloneCampaign.recipients.map(r => (
                      <option key={r.employee_id} value={r.employee_id}>
                        {r.employee_name || 'Employee'} ({r.recipient_email}) - {r.department || 'N/A'}
                      </option>
                    ))}
                  </select>
                </div>

                <div style={{ display: 'inline-flex', background: '#f1f5f9', borderRadius: 6, padding: 2 }}>
                  <button
                    onClick={() => setPreviewMode('html')}
                    style={{
                      background: previewMode === 'html' ? '#fff' : 'transparent',
                      border: 'none',
                      borderRadius: 4,
                      padding: '4px 10px',
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    HTML
                  </button>
                  <button
                    onClick={() => setPreviewMode('text')}
                    style={{
                      background: previewMode === 'text' ? '#fff' : 'transparent',
                      border: 'none',
                      borderRadius: 4,
                      padding: '4px 10px',
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    Plain Text
                  </button>
                </div>
              </div>

              {previewLoading ? (
                <div style={{ padding: 40, textAlign: 'center', color: '#64748b' }}>Rendering personalized template...</div>
              ) : previewResult ? (
                <div style={{ border: '1px solid #e2e8f0', borderRadius: 8, overflow: 'hidden' }}>
                  <div style={{ padding: '12px 16px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', fontSize: 13 }}>
                    <span style={{ fontWeight: 600, color: '#475569' }}>Subject: </span>
                    <span style={{ fontWeight: 700, color: '#0f172a' }}>{previewResult.rendered_subject}</span>
                  </div>

                  {previewMode === 'html' ? (
                    <div
                      style={{ padding: 20, background: '#fff', minHeight: 180, fontSize: 13 }}
                      dangerouslySetInnerHTML={{ __html: previewResult.rendered_html }}
                    />
                  ) : (
                    <pre style={{ padding: 20, background: '#fafafa', margin: 0, minHeight: 180, fontSize: 12, whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                      {previewResult.plain_text_fallback}
                    </pre>
                  )}

                  <div style={{ padding: '10px 16px', background: '#f8fafc', borderTop: '1px solid #e2e8f0', fontSize: 11, color: '#64748b', display: 'flex', gap: 14 }}>
                    <span>Resolved Tags: <strong>{previewResult.variables_used.join(', ') || 'None'}</strong></span>
                    {previewResult.missing_variables.length > 0 && (
                      <span style={{ color: '#dc2626' }}>Missing: <strong>{previewResult.missing_variables.join(', ')}</strong></span>
                    )}
                  </div>
                </div>
              ) : (
                <div style={{ padding: 40, textAlign: 'center', color: '#64748b' }}>
                  No preview generated for this recipient.
                </div>
              )}
            </div>

            <div style={{ padding: '14px 24px', borderTop: '1px solid #e2e8f0', textAlign: 'right' }}>
              <button
                onClick={() => setStandalonePreviewModal(false)}
                style={{ backgroundColor: '#0f172a', color: '#fff', border: 'none', borderRadius: 6, padding: '8px 16px', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
              >
                Close Preview
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  )
}
