'use client'

import React, { useState, useEffect } from 'react'
import AppLayout from '@/components/AppLayout'
import KPICard from '@/components/KPICard'
import Button from '@/components/Button'
import SearchInput from '@/components/SearchInput'
import Modal from '@/components/Modal'
import EmptyState from '@/components/EmptyState'
import {
  FileText,
  Plus,
  Eye,
  Copy,
  Trash2,
  Edit,
  Code,
  Tag,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Sparkles,
  RefreshCw,
  ExternalLink,
  Variable
} from 'lucide-react'

interface EmailTemplate {
  id: number
  template_name: string
  category: string
  subject: string
  body: string
  created_at: string
  updated_at: string
}

interface Employee {
  id: number
  employee_id: string
  full_name: string
  email: string
  department: string
  designation: string
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
  "General Announcement",
  "Training",
  "Finance",
  "Meeting",
  "HR Task",
  "Webinar",
  "Payment",
  "Technical Training",
  "Employee Onboarding",
  "Meeting Invitation",
  "Training Reminder",
  "Performance Review",
  "Webinar Invitation",
  "Task Deadline",
  "Other"
]

const VARIABLE_PANEL = [
  {
    group: "Employee Attributes",
    vars: [
      { tag: "{{ name }}", label: "Full Name" },
      { tag: "{{ email }}", label: "Email Address" },
      { tag: "{{ employee_id }}", label: "Employee Code" },
      { tag: "{{ department }}", label: "Department" },
      { tag: "{{ designation }}", label: "Job Title" },
      { tag: "{{ company }}", label: "Company" }
    ]
  },
  {
    group: "Event & Task Details",
    vars: [
      { tag: "{{ event_name }}", label: "Event Title" },
      { tag: "{{ event_date }}", label: "Date" },
      { tag: "{{ event_time }}", label: "Time" },
      { tag: "{{ event_location }}", label: "Location / Room" },
      { tag: "{{ meeting_link }}", label: "Meeting URL" },
      { tag: "{{ event_description }}", label: "Description" }
    ]
  },
  {
    group: "Sender Context",
    vars: [
      { tag: "{{ sender_name }}", label: "Sender Name" },
      { tag: "{{ sender_department }}", label: "Sender Dept" },
      { tag: "{{ company_name }}", label: "Company Name" }
    ]
  }
]

export default function TemplateManagementPage() {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [errorMsg, setErrorMsg] = useState<string>('')
  const [successMsg, setSuccessMsg] = useState<string>('')

  // Search & Filter
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [selectedCategory, setSelectedCategory] = useState<string>('All')

  // Selected Active Template for Studio Preview
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null)

  // Modals
  const [showEditorModal, setShowEditorModal] = useState<boolean>(false)
  const [showDeleteModal, setShowDeleteModal] = useState<boolean>(false)

  // Current Working Item
  const [currentTemplate, setCurrentTemplate] = useState<EmailTemplate | null>(null)

  // Editor Form State
  const [formName, setFormName] = useState<string>('')
  const [formCategory, setFormCategory] = useState<string>('General Announcement')
  const [formSubject, setFormSubject] = useState<string>('')
  const [formBody, setFormBody] = useState<string>('')
  const [activeTargetField, setActiveTargetField] = useState<'subject' | 'body'>('body')

  // Preview State
  const [previewEmployeeId, setPreviewEmployeeId] = useState<number | undefined>(undefined)
  const [previewTab, setPreviewTab] = useState<'html' | 'text'>('html')
  const [previewResult, setPreviewResult] = useState<PreviewResult | null>(null)
  const [previewLoading, setPreviewLoading] = useState<boolean>(false)

  useEffect(() => {
    fetchTemplates()
    fetchSampleEmployees()
  }, [searchTerm, selectedCategory])

  async function fetchTemplates() {
    setLoading(true)
    setErrorMsg('')
    try {
      const params = new URLSearchParams()
      if (searchTerm.trim()) params.append('search', searchTerm.trim())
      if (selectedCategory !== 'All') params.append('category', selectedCategory)

      const res = await fetch(`${API_URL}/api/templates?${params.toString()}`)
      if (res.ok) {
        const data = await res.json()
        const items = data.items || []
        setTemplates(items)
        if (items.length > 0 && selectedTemplateId === null) {
          setSelectedTemplateId(items[0].id)
        }
      } else {
        const err = await res.json()
        setErrorMsg(err.detail || 'Failed to fetch templates')
      }
    } catch (e: any) {
      setErrorMsg(`API error: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  async function fetchSampleEmployees() {
    try {
      const res = await fetch(`${API_URL}/api/employees?page_size=100`)
      if (res.ok) {
        const data = await res.json()
        const emps = data.items || []
        setEmployees(emps)
        if (emps.length > 0 && !previewEmployeeId) {
          setPreviewEmployeeId(emps[0].id)
        }
      }
    } catch (e) {
      console.warn('Failed to load employee list:', e)
    }
  }

  // Trigger live preview whenever selectedTemplateId or previewEmployeeId changes
  useEffect(() => {
    if (selectedTemplateId) {
      const active = templates.find((t) => t.id === selectedTemplateId)
      if (active) {
        triggerPreview(active.subject, active.body)
      }
    }
  }, [selectedTemplateId, previewEmployeeId, templates])

  async function triggerPreview(subjectToTest?: string, bodyToTest?: string) {
    setPreviewLoading(true)
    setPreviewResult(null)

    const active = templates.find((t) => t.id === selectedTemplateId)
    const subj = subjectToTest !== undefined ? subjectToTest : (active ? active.subject : formSubject)
    const bod = bodyToTest !== undefined ? bodyToTest : (active ? active.body : formBody)

    try {
      const res = await fetch(`${API_URL}/api/templates/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: subj,
          body: bod,
          employee_id: previewEmployeeId
        })
      })

      if (res.ok) {
        const data: PreviewResult = await res.json()
        setPreviewResult(data)
      } else {
        const err = await res.json()
        setPreviewResult({
          rendered_subject: subj,
          rendered_html: `<div style="color:red;padding:12px;">Error: ${err.detail || 'Failed to render preview'}</div>`,
          plain_text_fallback: '',
          variables_used: [],
          missing_variables: [],
          is_valid: false,
          validation_error: err.detail
        })
      }
    } catch (e: any) {
      setPreviewResult({
        rendered_subject: subj,
        rendered_html: `<div style="color:red;padding:12px;">Connection error: ${e.message}</div>`,
        plain_text_fallback: '',
        variables_used: [],
        missing_variables: [],
        is_valid: false,
        validation_error: e.message
      })
    } finally {
      setPreviewLoading(false)
    }
  }

  function openCreateModal() {
    setCurrentTemplate(null)
    setFormName('')
    setFormCategory('General Announcement')
    setFormSubject('Notification: {{ event_name }}')
    setFormBody(
      '<div style="font-family: Inter, system-ui, sans-serif; line-height: 1.6; color: #1e293b; max-width: 600px; margin: 0 auto; padding: 24px;">\n' +
      '  <h2 style="color: #0f172a; margin-top: 0;">Hello {{ name }},</h2>\n' +
      '  <p>This is an automated notification regarding <strong>{{ event_name }}</strong> scheduled for <strong>{{ event_date }}</strong> at <strong>{{ event_time }}</strong>.</p>\n' +
      '  <p>Location / Venue: {{ event_location }}</p>\n' +
      '  <div style="margin: 24px 0;">\n' +
      '    <a href="{{ meeting_link }}" style="background: #4f46e5; color: #ffffff; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600; display: inline-block;">Access Session</a>\n' +
      '  </div>\n' +
      '  <p style="color: #64748b; font-size: 14px;">Best regards,<br><strong style="color: #1e293b;">{{ sender_name }}</strong><br>{{ sender_department }} &bull; {{ company_name }}</p>\n' +
      '</div>'
    )
    setShowEditorModal(true)
  }

  function openEditModal(tmpl: EmailTemplate) {
    setCurrentTemplate(tmpl)
    setFormName(tmpl.template_name)
    setFormCategory(tmpl.category)
    setFormSubject(tmpl.subject)
    setFormBody(tmpl.body)
    setShowEditorModal(true)
  }

  function openDeleteModal(tmpl: EmailTemplate) {
    setCurrentTemplate(tmpl)
    setShowDeleteModal(true)
  }

  async function handleSaveTemplate(e: React.FormEvent) {
    e.preventDefault()
    setErrorMsg('')
    setSuccessMsg('')

    const payload = {
      template_name: formName.trim(),
      category: formCategory,
      subject: formSubject.trim(),
      body: formBody.trim()
    }

    try {
      const url = currentTemplate ? `${API_URL}/api/templates/${currentTemplate.id}` : `${API_URL}/api/templates`
      const method = currentTemplate ? 'PUT' : 'POST'

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (res.ok) {
        const saved = await res.json()
        setSuccessMsg(`Template '${formName}' saved successfully.`)
        setShowEditorModal(false)
        await fetchTemplates()
        setSelectedTemplateId(saved.id)
      } else {
        const err = await res.json()
        setErrorMsg(err.detail || 'Failed to save template. Please check syntax.')
      }
    } catch (e: any) {
      setErrorMsg(e.message)
    }
  }

  async function handleDuplicate(tmpl: EmailTemplate) {
    try {
      const res = await fetch(`${API_URL}/api/templates/${tmpl.id}/duplicate`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        setSuccessMsg(`Duplicated: Created '${data.template_name}'`)
        await fetchTemplates()
        setSelectedTemplateId(data.id)
      } else {
        const err = await res.json()
        setErrorMsg(err.detail || 'Could not duplicate template')
      }
    } catch (e: any) {
      setErrorMsg(e.message)
    }
  }

  async function handleDelete() {
    if (!currentTemplate) return
    try {
      const res = await fetch(`${API_URL}/api/templates/${currentTemplate.id}`, { method: 'DELETE' })
      if (res.ok) {
        setSuccessMsg(`Template '${currentTemplate.template_name}' removed.`)
        setShowDeleteModal(false)
        setCurrentTemplate(null)
        await fetchTemplates()
      } else {
        const err = await res.json()
        setErrorMsg(err.detail || 'Error deleting template')
      }
    } catch (e: any) {
      setErrorMsg(e.message)
    }
  }

  function insertTagIntoForm(tag: string) {
    if (activeTargetField === 'subject') {
      setFormSubject((prev) => prev + ' ' + tag)
    } else {
      setFormBody((prev) => prev + '\n' + tag)
    }
  }

  const activeTemplate = templates.find((t) => t.id === selectedTemplateId)

  return (
    <AppLayout
      title="Template Studio & Jinja2 Previews"
      subtitle="Author, personalize, and test HTML email templates with sandboxed Jinja2 variable rendering"
      actions={
        <Button
          variant="primary"
          icon={<Plus className="w-4 h-4" />}
          onClick={openCreateModal}
        >
          New Template
        </Button>
      }
    >
      {/* Alert Messages */}
      {successMsg && (
        <div className="mb-6 p-4 rounded-xl bg-teal-50 border border-teal-200 text-teal-800 text-sm flex items-center justify-between shadow-sm animate-fade-in">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-5 h-5 text-teal-600 flex-shrink-0" />
            <span className="font-medium">{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg('')} className="text-teal-600 hover:text-teal-800 text-xs font-semibold">
            Dismiss
          </button>
        </div>
      )}

      {errorMsg && (
        <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-center justify-between shadow-sm animate-fade-in">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            <span className="font-medium">{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg('')} className="text-rose-600 hover:text-rose-800 text-xs font-semibold">
            Dismiss
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
        <KPICard
          title="Total Templates"
          value={templates.length}
          icon={FileText}
          trendText="Catalog size in database"
          trendUp={true}
          accentColor="indigo"
          loading={loading}
        />
        <KPICard
          title="Template Categories"
          value={new Set(templates.map((t) => t.category)).size}
          icon={Layers}
          trendText="Organizational segments"
          trendUp={true}
          accentColor="teal"
          loading={loading}
        />
        <KPICard
          title="Variables Supported"
          value={VARIABLE_PANEL.reduce((acc, g) => acc + g.vars.length, 0)}
          icon={Variable}
          trendText="Sandboxed Jinja2 tags"
          trendUp={true}
          accentColor="purple"
          loading={loading}
        />
        <KPICard
          title="Active Preview Recipient"
          value={employees.length}
          icon={Sparkles}
          trendText="Available test personas"
          trendUp={true}
          accentColor="blue"
          loading={loading}
        />
      </div>

      {/* Main Split-Screen Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Template Catalog & Filter */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-base flex items-center space-x-2">
                <FileText className="w-4 h-4 text-indigo-600" />
                <span>Template Library</span>
              </h3>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                {templates.length} items
              </span>
            </div>

            <SearchInput
              value={searchTerm}
              onChange={(e: any) => setSearchTerm(typeof e === 'string' ? e : e.target.value)}
              onClear={() => setSearchTerm('')}
              placeholder="Search by template name or subject..."
            />

            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-1.5">
                Category Filter
              </label>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                aria-label="Filter templates by category"
                className="w-full bg-slate-50 border border-slate-200 text-slate-700 text-sm rounded-xl px-3.5 py-2.5 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>

            {/* List of Templates */}
            <div className="divide-y divide-slate-100 max-h-[520px] overflow-y-auto pr-1">
              {templates.length === 0 ? (
                <div className="py-8 text-center text-sm text-slate-400">
                  No templates found matching your search.
                </div>
              ) : (
                templates.map((tmpl) => {
                  const isSelected = tmpl.id === selectedTemplateId
                  return (
                    <div
                      key={tmpl.id}
                      onClick={() => setSelectedTemplateId(tmpl.id)}
                      className={`p-3.5 rounded-xl transition-all cursor-pointer mb-1.5 ${
                        isSelected
                          ? 'bg-indigo-50/80 border border-indigo-200 shadow-sm'
                          : 'hover:bg-slate-50 border border-transparent'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <p className={`font-semibold text-sm ${isSelected ? 'text-indigo-950' : 'text-slate-900'}`}>
                            {tmpl.template_name}
                          </p>
                          <p className="text-xs text-slate-500 mt-0.5">
                            Subject: {tmpl.subject}
                          </p>
                          <div className="flex items-center space-x-2 mt-2">
                            <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-600">
                              {tmpl.category}
                            </span>
                            <span className="text-[11px] font-mono text-slate-400">
                              ID: #{tmpl.id}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center space-x-1" onClick={(e) => e.stopPropagation()}>
                          <button
                            title="Edit template"
                            onClick={() => openEditModal(tmpl)}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-white transition-colors"
                          >
                            <Edit className="w-3.5 h-3.5" />
                          </button>
                          <button
                            title="Duplicate template"
                            onClick={() => handleDuplicate(tmpl)}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-teal-600 hover:bg-white transition-colors"
                          >
                            <Copy className="w-3.5 h-3.5" />
                          </button>
                          <button
                            title="Delete template"
                            onClick={() => openDeleteModal(tmpl)}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-white transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Live Sandboxed Jinja2 Preview Studio */}
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-5 border-b border-slate-100 gap-3">
              <div>
                <h3 className="font-bold text-slate-900 text-lg flex items-center space-x-2">
                  <Sparkles className="w-5 h-5 text-indigo-600" />
                  <span>Jinja2 Live Preview Studio</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Real-time sandboxed rendering with real recipient context
                </p>
              </div>

              {/* Employee Persona Picker */}
              <div className="flex items-center space-x-2">
                <span className="text-xs font-semibold text-slate-500 whitespace-nowrap">
                  Persona:
                </span>
                <select
                  value={previewEmployeeId}
                  onChange={(e) => setPreviewEmployeeId(Number(e.target.value))}
                  aria-label="Select recipient persona"
                  className="bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-xl px-3 py-2 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                >
                  {employees.map((emp) => (
                    <option key={emp.id} value={emp.id}>
                      {emp.full_name} ({emp.employee_id} - {emp.department})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Validation Banner if missing variables or errors */}
            {previewResult && !previewResult.is_valid && (
              <div className="mt-4 p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs space-y-1">
                <div className="flex items-center space-x-2 font-bold text-amber-800">
                  <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
                  <span>Jinja2 Variable Notice</span>
                </div>
                {previewResult.missing_variables && previewResult.missing_variables.length > 0 && (
                  <p>
                    Undefined / missing context variable(s):{' '}
                    <span className="font-mono font-semibold">
                      {previewResult.missing_variables.join(', ')}
                    </span>
                  </p>
                )}
                {previewResult.validation_error && (
                  <p className="font-mono text-amber-700">{previewResult.validation_error}</p>
                )}
              </div>
            )}

            {/* Rendered Subject Header */}
            <div className="mt-5 p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span className="font-semibold uppercase tracking-wider">Subject Preview:</span>
                <span className="font-mono text-[11px] text-slate-400">
                  {previewResult?.variables_used?.length || 0} variables substituted
                </span>
              </div>
              <p className="text-base font-bold text-slate-900">
                {previewResult ? previewResult.rendered_subject : activeTemplate?.subject || '—'}
              </p>
            </div>

            {/* View Mode Tabs (HTML / Plain Text) */}
            <div className="flex items-center justify-between mt-5 mb-3">
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setPreviewTab('html')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                    previewTab === 'html'
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  HTML Preview
                </button>
                <button
                  onClick={() => setPreviewTab('text')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                    previewTab === 'text'
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  Plain-Text Fallback
                </button>
              </div>

              {activeTemplate && (
                <Button
                  variant="outline"
                  size="sm"
                  icon={<Edit className="w-3.5 h-3.5" />}
                  onClick={() => openEditModal(activeTemplate)}
                >
                  Edit Template
                </Button>
              )}
            </div>

            {/* Sandboxed Iframe Container */}
            <div className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-inner min-h-[380px] relative">
              {previewLoading && (
                <div className="absolute inset-0 bg-white/70 backdrop-blur-xs flex items-center justify-center z-10">
                  <div className="flex items-center space-x-2 text-indigo-600 font-medium text-xs">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Rendering template...</span>
                  </div>
                </div>
              )}

              {previewTab === 'html' ? (
                <iframe
                  title="Template HTML Preview"
                  sandbox=""
                  srcDoc={previewResult ? previewResult.rendered_html : activeTemplate?.body || ''}
                  className="w-full h-[420px] border-0"
                />
              ) : (
                <pre className="p-4 text-xs font-mono text-slate-700 whitespace-pre-wrap h-[420px] overflow-y-auto bg-slate-50/50">
                  {previewResult ? previewResult.plain_text_fallback : 'No plain text representation available.'}
                </pre>
              )}
            </div>

            {/* Available Tags Catalog */}
            <div className="mt-6 pt-5 border-t border-slate-100">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center space-x-1.5">
                <Tag className="w-3.5 h-3.5 text-slate-400" />
                <span>Available Personalization Variables</span>
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {VARIABLE_PANEL.map((group) => (
                  <div key={group.group} className="bg-slate-50/70 rounded-xl p-3 border border-slate-200/60">
                    <p className="text-[11px] font-bold text-slate-700 mb-2">{group.group}</p>
                    <div className="space-y-1">
                      {group.vars.map((v) => (
                        <div key={v.tag} className="flex items-center justify-between text-xs">
                          <code className="font-mono text-[11px] text-indigo-600 font-bold bg-white px-1.5 py-0.5 rounded border border-slate-200">
                            {v.tag}
                          </code>
                          <span className="text-[11px] text-slate-500">{v.label}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Template Editor Modal */}
      <Modal
        isOpen={showEditorModal}
        onClose={() => setShowEditorModal(false)}
        title={currentTemplate ? `Edit Template: ${currentTemplate.template_name}` : 'Create New Email Template'}
        subtitle="Configure Jinja2 template content, category, and subject format"
        size="2xl"
      >
        <form onSubmit={handleSaveTemplate} className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-600 block mb-1.5">
                Template Name *
              </label>
              <input
                type="text"
                required
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="e.g. Q4 Performance Appraisal"
                className="w-full bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-xl px-3.5 py-2.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-600 block mb-1.5">
                Category *
              </label>
              <select
                value={formCategory}
                onChange={(e) => setFormCategory(e.target.value)}
                aria-label="Select template category"
                className="w-full bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-xl px-3.5 py-2.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              >
                {CATEGORIES.filter((c) => c !== 'All').map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-600">
                Email Subject Line *
              </label>
              <button
                type="button"
                onClick={() => setActiveTargetField('subject')}
                className={`text-xs font-semibold px-2 py-0.5 rounded ${
                  activeTargetField === 'subject'
                    ? 'bg-indigo-100 text-indigo-700'
                    : 'text-slate-400 hover:text-slate-600'
                }`}
              >
                Insert Tags Here
              </button>
            </div>
            <input
              type="text"
              required
              spellCheck={false}
              value={formSubject}
              onFocus={() => setActiveTargetField('subject')}
              onChange={(e) => setFormSubject(e.target.value)}
              placeholder="e.g. Reminder: {{ event_name }} for {{ name }}"
              className="w-full bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-xl px-3.5 py-2.5 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-600">
                Email HTML Body *
              </label>
              <button
                type="button"
                onClick={() => setActiveTargetField('body')}
                className={`text-xs font-semibold px-2 py-0.5 rounded ${
                  activeTargetField === 'body'
                    ? 'bg-indigo-100 text-indigo-700'
                    : 'text-slate-400 hover:text-slate-600'
                }`}
              >
                Insert Tags Here
              </button>
            </div>
            <textarea
              required
              rows={9}
              spellCheck={false}
              autoCapitalize="off"
              autoComplete="off"
              autoCorrect="off"
              value={formBody}
              onFocus={() => setActiveTargetField('body')}
              onChange={(e) => setFormBody(e.target.value)}
              placeholder="Enter HTML and Jinja2 markup here..."
              className="w-full bg-slate-50 border border-slate-200 text-slate-900 text-xs font-mono rounded-xl p-3.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none leading-relaxed"
            />
          </div>

          {/* Quick Insert Variables Toolbar */}
          <div className="bg-slate-50 rounded-xl p-3 border border-slate-200">
            <span className="text-[11px] font-bold text-slate-500 block mb-2">
              Click to insert tag into {activeTargetField}:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {['{{ name }}', '{{ email }}', '{{ department }}', '{{ event_name }}', '{{ event_date }}', '{{ event_time }}', '{{ meeting_link }}', '{{ sender_name }}', '{{ company_name }}'].map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => insertTagIntoForm(tag)}
                  className="px-2 py-1 bg-white hover:bg-indigo-50 text-indigo-700 border border-slate-200 rounded text-xs font-mono font-medium transition-colors"
                >
                  + {tag}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-200">
            <Button variant="ghost" type="button" onClick={() => setShowEditorModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit">
              {currentTemplate ? 'Save Template Changes' : 'Create Template'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Template"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            Are you sure you want to permanently delete template{' '}
            <strong className="text-slate-900 font-semibold">
              &quot;{currentTemplate?.template_name}&quot;
            </strong>?
            This operation cannot be undone.
          </p>

          <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-200">
            <Button variant="ghost" onClick={() => setShowDeleteModal(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={handleDelete}>
              Confirm Delete
            </Button>
          </div>
        </div>
      </Modal>
    </AppLayout>
  )
}
