'use client'

import React, { useState, useEffect } from 'react'
import AppLayout from '../../components/AppLayout'
import KPICard from '../../components/KPICard'
import StatusBadge from '../../components/StatusBadge'
import Button from '../../components/Button'
import SearchInput from '../../components/SearchInput'
import Modal from '../../components/Modal'
import Drawer from '../../components/Drawer'
import EmptyState from '../../components/EmptyState'
import {
  Megaphone,
  CheckCircle2,
  Clock,
  FileCode,
  Users,
  Plus,
  Search,
  Filter,
  Eye,
  Trash2,
  Edit,
  ArrowRight,
  ArrowLeft,
  Calendar,
  Sparkles,
  Send,
  AlertCircle,
  RotateCcw,
  UserCheck,
  Check,
  Building2,
  Mail,
  HelpCircle,
  FileText
} from 'lucide-react'

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

  // Preview State
  const [previewEmpId, setPreviewEmpId] = useState<number | null>(null)
  const [previewResult, setPreviewResult] = useState<PreviewResult | null>(null)
  const [previewLoading, setPreviewLoading] = useState<boolean>(false)
  const [previewMode, setPreviewMode] = useState<'html' | 'text'>('html')

  // Detail Drawer State
  const [currentCampaign, setCurrentCampaign] = useState<CampaignDetail | null>(null)
  const [showDetailDrawer, setShowDetailDrawer] = useState<boolean>(false)
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

  useEffect(() => {
    fetchCampaigns()
  }, [searchTerm, statusFilter, categoryFilter])

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
        setShowDetailDrawer(true)
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
        if (showDetailDrawer) setShowDetailDrawer(false)
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
    setStandaloneSelectedEmpId(empId)
    try {
      const res = await fetch(`${API_URL}/api/campaigns/${campId}/preview/${empId}`)
      if (res.ok) {
        const data = await res.json()
        setPreviewResult(data)
      } else {
        const err = await res.json()
        showNotification(err.detail || 'Failed to generate preview', true)
      }
    } catch (e: any) {
      showNotification(e.message, true)
    } finally {
      setPreviewLoading(false)
    }
  }

  return (
    <AppLayout
      title="Email Campaign Studio"
      subtitle="Design, segment, orchestrate, and schedule personalized multi-recipient email broadcasts"
      breadcrumbs={[{ label: 'Campaigns' }]}
      actions={
        <Button
          variant="primary"
          size="sm"
          icon={Plus}
          onClick={openCreateWizard}
        >
          Create Campaign
        </Button>
      }
    >
      {/* Notifications */}
      {successMsg && (
        <div className="flex items-center justify-between p-4 mb-6 rounded-xl bg-emerald-50 border border-emerald-200 text-sm text-emerald-800 animate-in fade-in">
          <div className="flex items-center gap-2.5 font-medium">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button
            onClick={() => setSuccessMsg('')}
            className="text-xs font-semibold uppercase opacity-60 hover:opacity-100"
          >
            Dismiss
          </button>
        </div>
      )}

      {errorMsg && (
        <div className="flex items-center justify-between p-4 mb-6 rounded-xl bg-rose-50 border border-rose-200 text-sm text-rose-800 animate-in fade-in">
          <div className="flex items-center gap-2.5 font-medium">
            <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={() => setErrorMsg('')}
            className="text-xs font-semibold uppercase opacity-60 hover:opacity-100"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* 5 KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">
        <KPICard
          title="Total Campaigns"
          value={stats?.total_campaigns ?? 0}
          icon={Megaphone}
          accent="indigo"
          subtitle="All campaign records"
          loading={loading && !stats}
        />
        <KPICard
          title="Ready to Send"
          value={stats?.ready_campaigns ?? 0}
          icon={Send}
          accent="emerald"
          subtitle="Awaiting schedule trigger"
          loading={loading && !stats}
        />
        <KPICard
          title="Drafts"
          value={stats?.draft_campaigns ?? 0}
          icon={FileText}
          accent="slate"
          subtitle="In preparation"
          loading={loading && !stats}
        />
        <KPICard
          title="Scheduled"
          value={stats?.scheduled_campaigns ?? 0}
          icon={Clock}
          accent="blue"
          subtitle="Future UTC dispatch"
          loading={loading && !stats}
        />
        <KPICard
          title="Targeted Recipients"
          value={stats?.total_recipients_targeted ?? 0}
          icon={Users}
          accent="teal"
          subtitle="Total linked contacts"
          loading={loading && !stats}
        />
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs mb-6">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <div className="flex-1 max-w-md">
            <SearchInput
              value={searchTerm}
              onChange={setSearchTerm}
              placeholder="Search campaigns by name, category, or template..."
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Category Filter */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-500 whitespace-nowrap">Category:</span>
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="text-xs py-2 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none shadow-xs"
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-500 whitespace-nowrap">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="text-xs py-2 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none shadow-xs"
              >
                {STATUS_LIST.map((stat) => (
                  <option key={stat} value={stat}>
                    {stat}
                  </option>
                ))}
              </select>
            </div>

            {(searchTerm || categoryFilter !== 'All' || statusFilter !== 'ALL') && (
              <Button
                variant="ghost"
                size="sm"
                icon={RotateCcw}
                onClick={() => {
                  setSearchTerm('')
                  setCategoryFilter('All')
                  setStatusFilter('ALL')
                }}
              >
                Reset
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Main Campaign Directory Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        {loading && campaigns.length === 0 ? (
          <div className="p-12 text-center text-sm text-slate-400">
            Loading campaign records...
          </div>
        ) : campaigns.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No campaigns found"
              description="No campaigns match your filters. Create your first campaign to begin targeting recipients."
              icon={Megaphone}
              actionLabel="Create Campaign"
              onAction={openCreateWizard}
              actionIcon={Plus}
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-[#F8FAFC] text-slate-600 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">ID</th>
                  <th className="py-3 px-4">Campaign Name</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Associated Template</th>
                  <th className="py-3 px-4">Recipients</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Scheduled / Created</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {campaigns.map((camp) => (
                  <tr key={camp.id} className="hover:bg-slate-50/70 transition-colors group">
                    <td className="py-3.5 px-4 font-mono text-xs font-bold text-slate-500">
                      #{camp.id}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="max-w-xs">
                        <p className="font-semibold text-slate-900 leading-tight truncate">
                          {camp.campaign_name}
                        </p>
                        {camp.description && (
                          <p className="text-xs text-slate-400 truncate mt-0.5">
                            {camp.description}
                          </p>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
                        {camp.category}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-xs text-slate-700">
                      <div className="flex items-center gap-1.5 truncate max-w-[180px]">
                        <FileCode className="w-3.5 h-3.5 text-indigo-500 flex-shrink-0" />
                        <span className="truncate">{camp.template_name || 'No template'}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
                        <Users className="w-3 h-3" />
                        {camp.recipient_count}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <StatusBadge status={camp.status} size="sm" />
                    </td>
                    <td className="py-3.5 px-4 text-xs text-slate-500 font-mono whitespace-nowrap">
                      {camp.scheduled_at
                        ? camp.scheduled_at.replace('T', ' ').slice(0, 16)
                        : camp.created_at.replace('T', ' ').slice(0, 10)}
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => openStandalonePreview(camp.id)}
                          title="Preview Email"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => openCampaignDetail(camp.id)}
                          title="View & Edit Details"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteCampaign(camp.id, camp.campaign_name)}
                          title="Delete Campaign"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="px-4 py-3 bg-slate-50/50 border-t border-slate-200 text-xs text-slate-500 flex items-center justify-between">
          <span>Showing {campaigns.length} campaigns</span>
          <span>Orchestrator: Unified Campaign Engine</span>
        </div>
      </div>

      {/* CREATE CAMPAIGN WIZARD MODAL */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create Email Campaign"
        subtitle={`Step ${wizardStep} of 4: ${
          wizardStep === 1
            ? 'Campaign Information'
            : wizardStep === 2
            ? 'Template Selection'
            : wizardStep === 3
            ? 'Target Recipients'
            : 'Scheduling & Preview'
        }`}
        maxWidth="3xl"
      >
        {/* Stepper Indicator */}
        <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-100">
          {[
            { num: 1, label: 'Details' },
            { num: 2, label: 'Template' },
            { num: 3, label: 'Recipients' },
            { num: 4, label: 'Review' },
          ].map((st) => (
            <div key={st.num} className="flex items-center gap-2">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                  wizardStep === st.num
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : wizardStep > st.num
                    ? 'bg-emerald-600 text-white'
                    : 'bg-slate-100 text-slate-500'
                }`}
              >
                {wizardStep > st.num ? <Check className="w-3.5 h-3.5" /> : st.num}
              </div>
              <span
                className={`text-xs font-medium ${
                  wizardStep === st.num ? 'text-slate-900 font-bold' : 'text-slate-500'
                }`}
              >
                {st.label}
              </span>
            </div>
          ))}
        </div>

        {/* STEP 1: Details */}
        {wizardStep === 1 && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Campaign Name *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Q4 Performance Appraisal Briefing"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                className="w-full text-sm py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Category *
              </label>
              <select
                value={formCategory}
                onChange={(e) => setFormCategory(e.target.value)}
                className="w-full text-sm py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              >
                {CATEGORIES.filter((c) => c !== 'All').map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Description / Purpose
              </label>
              <textarea
                rows={3}
                placeholder="Optional operational brief or objective..."
                value={formDesc}
                onChange={(e) => setFormDesc(e.target.value)}
                className="w-full text-sm py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
              <Button variant="secondary" onClick={() => setShowCreateModal(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                icon={ArrowRight}
                iconPosition="right"
                onClick={() => {
                  if (!formName.trim()) {
                    showNotification('Please enter a campaign name', true)
                    return
                  }
                  setWizardStep(2)
                }}
              >
                Next: Select Template
              </Button>
            </div>
          </div>
        )}

        {/* STEP 2: Template Selection */}
        {wizardStep === 2 && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Choose Email Template *
              </label>
              <select
                value={formTemplateId || ''}
                onChange={(e) => setFormTemplateId(Number(e.target.value))}
                className="w-full text-sm py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              >
                {templates.map((tmpl) => (
                  <option key={tmpl.id} value={tmpl.id}>
                    [{tmpl.category}] {tmpl.template_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Template Preview Snippet */}
            {formTemplateId && (
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                {(() => {
                  const selectedTmpl = templates.find((t) => t.id === formTemplateId)
                  if (!selectedTmpl) return null
                  return (
                    <div>
                      <p className="font-semibold text-slate-900 mb-1">
                        Subject: <span className="font-normal">{selectedTmpl.subject}</span>
                      </p>
                      <p className="font-semibold text-slate-900 mb-2">
                        Category: <span className="font-normal">{selectedTmpl.category}</span>
                      </p>
                      <div className="border border-slate-200 rounded-lg bg-white p-3 font-mono text-[11px] text-slate-600 max-h-36 overflow-y-auto whitespace-pre-wrap">
                        {selectedTmpl.body}
                      </div>
                    </div>
                  )
                })()}
              </div>
            )}

            <div className="flex justify-between pt-4 border-t border-slate-100">
              <Button variant="secondary" icon={ArrowLeft} onClick={() => setWizardStep(1)}>
                Back
              </Button>
              <Button
                variant="primary"
                icon={ArrowRight}
                iconPosition="right"
                onClick={() => setWizardStep(3)}
              >
                Next: Target Recipients
              </Button>
            </div>
          </div>
        )}

        {/* STEP 3: Recipient Targeting */}
        {wizardStep === 3 && (
          <div className="space-y-4">
            {/* Quick Actions & Filters */}
            <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex items-center gap-2">
                <Button variant="secondary" size="sm" onClick={handleSelectAllActive}>
                  Select All Active ({employees.filter((e) => e.employment_status === 'Active').length})
                </Button>
                <Button variant="secondary" size="sm" onClick={handleSelectFiltered}>
                  Select Filtered
                </Button>
                <Button variant="ghost" size="sm" onClick={handleDeselectAll}>
                  Clear
                </Button>
              </div>

              <div className="text-xs font-semibold text-indigo-700 bg-indigo-50 px-3 py-1 rounded-full border border-indigo-200">
                Selected: {selectedEmpIds.length} recipients
              </div>
            </div>

            {/* Department Filter & Search */}
            <div className="grid grid-cols-2 gap-3">
              <SearchInput
                value={wizardEmpSearch}
                onChange={setWizardEmpSearch}
                placeholder="Search employees..."
              />
              <select
                value={wizardDeptFilter}
                onChange={(e) => setWizardDeptFilter(e.target.value)}
                className="text-xs py-2 px-3 bg-white border border-slate-200 rounded-lg text-slate-800"
              >
                <option value="All">All Departments</option>
                {departmentsList.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>

            {/* Employee Checkbox List */}
            <div className="max-h-60 overflow-y-auto border border-slate-200 rounded-xl divide-y divide-slate-100">
              {getFilteredEmployees().map((emp) => {
                const isSelected = selectedEmpIds.includes(emp.id)
                return (
                  <label
                    key={emp.id}
                    className={`flex items-center justify-between p-3 cursor-pointer text-xs transition-colors hover:bg-slate-50 ${
                      isSelected ? 'bg-indigo-50/40' : ''
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleEmployeeSelection(emp.id)}
                        className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                      />
                      <div>
                        <span className="font-semibold text-slate-900">{emp.full_name}</span>
                        <span className="text-slate-400 ml-1.5 font-mono">{emp.email}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] bg-slate-100 text-slate-600 border border-slate-200">
                        {emp.department}
                      </span>
                      <StatusBadge status={emp.employment_status} size="sm" />
                    </div>
                  </label>
                )
              })}
            </div>

            <div className="flex justify-between pt-4 border-t border-slate-100">
              <Button variant="secondary" icon={ArrowLeft} onClick={() => setWizardStep(2)}>
                Back
              </Button>
              <Button
                variant="primary"
                icon={ArrowRight}
                iconPosition="right"
                onClick={() => {
                  if (selectedEmpIds.length === 0) {
                    showNotification('Please select at least one recipient', true)
                    return
                  }
                  setWizardStep(4)
                  if (selectedEmpIds.length > 0) {
                    triggerWizardPreview(selectedEmpIds[0])
                  }
                }}
              >
                Next: Review & Schedule
              </Button>
            </div>
          </div>
        )}

        {/* STEP 4: Review & Schedule */}
        {wizardStep === 4 && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Schedule Execution (Optional)
                </label>
                <input
                  type="datetime-local"
                  value={formScheduledAt}
                  onChange={(e) => setFormScheduledAt(e.target.value)}
                  className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Leave blank for immediate trigger when marked ready.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Preview Recipient
                </label>
                <select
                  value={previewEmpId || ''}
                  onChange={(e) => triggerWizardPreview(Number(e.target.value))}
                  className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                >
                  {selectedEmpIds.map((id) => {
                    const emp = employees.find((e) => e.id === id)
                    return (
                      <option key={id} value={id}>
                        {emp?.full_name} ({emp?.email})
                      </option>
                    )
                  })}
                </select>
              </div>
            </div>

            {/* Sandboxed HTML Email Preview */}
            <div className="border border-slate-200 rounded-xl overflow-hidden shadow-xs">
              <div className="flex items-center justify-between px-4 py-2.5 bg-slate-50 border-b border-slate-200 text-xs">
                <span className="font-semibold text-slate-700">
                  Subject:{' '}
                  <span className="text-slate-900 font-bold">
                    {previewResult?.rendered_subject || 'Loading subject...'}
                  </span>
                </span>
                <div className="flex gap-1">
                  <button
                    onClick={() => setPreviewMode('html')}
                    className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                      previewMode === 'html'
                        ? 'bg-indigo-600 text-white'
                        : 'text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    HTML
                  </button>
                  <button
                    onClick={() => setPreviewMode('text')}
                    className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                      previewMode === 'text'
                        ? 'bg-indigo-600 text-white'
                        : 'text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    Text
                  </button>
                </div>
              </div>

              {previewLoading ? (
                <div className="p-8 text-center text-xs text-slate-400">
                  Rendering sandboxed email preview...
                </div>
              ) : previewResult ? (
                previewMode === 'html' ? (
                  <iframe
                    title="Recipient Email Preview"
                    sandbox=""
                    srcDoc={previewResult.rendered_html}
                    className="w-full min-h-[220px] border-none bg-white"
                  />
                ) : (
                  <pre className="p-4 bg-slate-50 text-xs font-mono whitespace-pre-wrap text-slate-700 max-h-56 overflow-y-auto">
                    {previewResult.plain_text_fallback}
                  </pre>
                )
              ) : (
                <div className="p-8 text-center text-xs text-slate-400">No preview generated</div>
              )}
            </div>

            <div className="flex items-center justify-between pt-4 border-t border-slate-100">
              <Button variant="secondary" icon={ArrowLeft} onClick={() => setWizardStep(3)}>
                Back
              </Button>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={() => handleSaveCampaign('DRAFT')}>
                  Save as Draft
                </Button>
                <Button variant="primary" icon={Check} onClick={() => handleSaveCampaign('READY')}>
                  Mark Ready to Send
                </Button>
              </div>
            </div>
          </div>
        )}
      </Modal>

      {/* CAMPAIGN DETAIL & EDIT DRAWER */}
      <Drawer
        isOpen={showDetailDrawer}
        onClose={() => setShowDetailDrawer(false)}
        title={currentCampaign?.campaign_name || 'Campaign Details'}
        subtitle={`ID #${currentCampaign?.id} • Category: ${currentCampaign?.category}`}
        size="xl"
      >
        {currentCampaign && (
          <div className="space-y-6">
            {/* Top Overview Cards */}
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <div className="text-[11px] text-slate-500 font-semibold uppercase">Status</div>
                <div className="mt-1">
                  <StatusBadge status={currentCampaign.status} />
                </div>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <div className="text-[11px] text-slate-500 font-semibold uppercase">Recipients</div>
                <div className="mt-1 text-base font-bold text-slate-900">
                  {currentCampaign.recipients.length} targeted
                </div>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <div className="text-[11px] text-slate-500 font-semibold uppercase">Template</div>
                <div className="mt-1 text-xs font-medium text-slate-800 truncate" title={currentCampaign.template?.template_name}>
                  {currentCampaign.template?.template_name || 'None'}
                </div>
              </div>
            </div>

            {/* Edit / View Mode */}
            {isEditing ? (
              <div className="space-y-4 p-4 rounded-xl border border-indigo-200 bg-indigo-50/30">
                <h4 className="text-xs font-bold text-indigo-900 uppercase tracking-wider">
                  Edit Campaign Settings
                </h4>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Name</label>
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg bg-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Status</label>
                  <select
                    value={editStatus}
                    onChange={(e) => setEditStatus(e.target.value)}
                    className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg bg-white"
                  >
                    <option value="DRAFT">DRAFT</option>
                    <option value="READY">READY</option>
                    <option value="SCHEDULED">SCHEDULED</option>
                    <option value="COMPLETED">COMPLETED</option>
                    <option value="CANCELLED">CANCELLED</option>
                  </select>
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="secondary" size="sm" onClick={() => setIsEditing(false)}>
                    Cancel
                  </Button>
                  <Button variant="primary" size="sm" onClick={handleUpdateCampaign}>
                    Save Changes
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex justify-end">
                <Button variant="secondary" size="sm" icon={Edit} onClick={() => setIsEditing(true)}>
                  Edit Campaign Settings
                </Button>
              </div>
            )}

            {/* Targeted Recipients Table */}
            <div>
              <h4 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
                <Users className="w-4 h-4 text-indigo-600" />
                Targeted Recipients ({currentCampaign.recipients.length})
              </h4>
              <div className="border border-slate-200 rounded-xl overflow-hidden max-h-72 overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 sticky top-0">
                    <tr>
                      <th className="py-2.5 px-3">Recipient</th>
                      <th className="py-2.5 px-3">Department</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {currentCampaign.recipients.map((r) => (
                      <tr key={r.id} className="hover:bg-slate-50">
                        <td className="py-2.5 px-3 font-medium text-slate-900">
                          {r.employee_name || r.recipient_email}
                          <div className="text-[10px] text-slate-400 font-mono">{r.recipient_email}</div>
                        </td>
                        <td className="py-2.5 px-3 text-slate-600">{r.department || 'General'}</td>
                        <td className="py-2.5 px-3">
                          <StatusBadge status={r.status} size="sm" />
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <button
                            onClick={() => handleRemoveRecipient(currentCampaign.id, r.employee_id)}
                            className="text-rose-600 hover:text-rose-800 text-[11px] font-semibold"
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
          </div>
        )}
      </Drawer>

      {/* STANDALONE EMAIL PREVIEW MODAL */}
      <Modal
        isOpen={standalonePreviewModal}
        onClose={() => setStandalonePreviewModal(false)}
        title="Personalized Email Preview"
        subtitle={`Campaign: ${standaloneCampaign?.campaign_name || ''}`}
        maxWidth="3xl"
      >
        <div className="space-y-4">
          {standaloneCampaign && standaloneCampaign.recipients.length > 0 && (
            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold text-slate-700 whitespace-nowrap">
                Recipient Context:
              </span>
              <select
                value={standaloneSelectedEmpId || ''}
                onChange={(e) =>
                  loadStandalonePreview(standaloneCampaign.id, Number(e.target.value))
                }
                className="text-xs py-2 px-3 border border-slate-200 rounded-lg flex-1 bg-white focus:ring-2 focus:ring-indigo-500"
              >
                {standaloneCampaign.recipients.map((r) => (
                  <option key={r.employee_id} value={r.employee_id}>
                    {r.employee_name || r.recipient_email} ({r.recipient_email})
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="border border-slate-200 rounded-xl overflow-hidden shadow-xs">
            <div className="flex items-center justify-between px-4 py-2.5 bg-slate-50 border-b border-slate-200 text-xs">
              <span className="font-semibold text-slate-700">
                Subject:{' '}
                <span className="text-slate-900 font-bold">
                  {previewResult?.rendered_subject || 'Loading subject...'}
                </span>
              </span>
              <div className="flex gap-1">
                <button
                  onClick={() => setPreviewMode('html')}
                  className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                    previewMode === 'html'
                      ? 'bg-indigo-600 text-white'
                      : 'text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  HTML
                </button>
                <button
                  onClick={() => setPreviewMode('text')}
                  className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                    previewMode === 'text'
                      ? 'bg-indigo-600 text-white'
                      : 'text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  Text
                </button>
              </div>
            </div>

            {previewLoading ? (
              <div className="p-12 text-center text-xs text-slate-400">
                Rendering sandboxed email preview...
              </div>
            ) : previewResult ? (
              previewMode === 'html' ? (
                <iframe
                  title="Recipient Email Preview"
                  sandbox=""
                  srcDoc={previewResult.rendered_html}
                  className="w-full min-h-[260px] border-none bg-white"
                />
              ) : (
                <pre className="p-4 bg-slate-50 text-xs font-mono whitespace-pre-wrap text-slate-700 max-h-60 overflow-y-auto">
                  {previewResult.plain_text_fallback}
                </pre>
              )
            ) : (
              <div className="p-8 text-center text-xs text-slate-400">
                No recipients to preview
              </div>
            )}
          </div>

          <div className="flex justify-end pt-3 border-t border-slate-100">
            <Button variant="secondary" onClick={() => setStandalonePreviewModal(false)}>
              Close
            </Button>
          </div>
        </div>
      </Modal>
    </AppLayout>
  )
}
