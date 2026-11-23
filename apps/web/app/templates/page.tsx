'use client'

import React, { useState, useEffect } from 'react'

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

const VARIABLE_PANEL = [
  {
    group: "Employee Variables",
    vars: [
      { tag: "{{ name }}", label: "Full Name" },
      { tag: "{{ email }}", label: "Email" },
      { tag: "{{ employee_id }}", label: "Employee Code" },
      { tag: "{{ department }}", label: "Department" },
      { tag: "{{ designation }}", label: "Job Title" },
      { tag: "{{ company }}", label: "Company" }
    ]
  },
  {
    group: "Event Variables",
    vars: [
      { tag: "{{ event_name }}", label: "Event Title" },
      { tag: "{{ event_date }}", label: "Date" },
      { tag: "{{ event_time }}", label: "Time" },
      { tag: "{{ event_location }}", label: "Venue/Room" },
      { tag: "{{ meeting_link }}", label: "Meeting URL" },
      { tag: "{{ event_description }}", label: "Description" }
    ]
  },
  {
    group: "Sender Variables",
    vars: [
      { tag: "{{ sender_name }}", label: "Sender Name" },
      { tag: "{{ sender_department }}", label: "Sender Dept" },
      { tag: "{{ company_name }}", label: "Org Name" }
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

  // Modals
  const [showEditorModal, setShowEditorModal] = useState<boolean>(false)
  const [showDeleteModal, setShowDeleteModal] = useState<boolean>(false)
  const [showPreviewModal, setShowPreviewModal] = useState<boolean>(false)

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
        setTemplates(data.items || [])
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
        setEmployees(data.items || [])
        if (data.items && data.items.length > 0 && !previewEmployeeId) {
          setPreviewEmployeeId(data.items[0].id)
        }
      }
    } catch (e) {
      console.warn('Failed to load employee list for preview context:', e)
    }
  }

  function openCreateModal() {
    setCurrentTemplate(null)
    setFormName('')
    setFormCategory('General Announcement')
    setFormSubject('Reminder: {{ event_name }}')
    setFormBody(
      '<div style="font-family: sans-serif; line-height: 1.6; color: #1e293b;">\n' +
      '  <h2 style="color: #0f172a;">Hello {{ name }},</h2>\n' +
      '  <p>This is a notification regarding <strong>{{ event_name }}</strong> scheduled for <strong>{{ event_date }}</strong> at <strong>{{ event_time }}</strong>.</p>\n' +
      '  <p>Location: {{ event_location }}</p>\n' +
      '  <div style="margin: 20px 0;">\n' +
      '    <a href="{{ meeting_link }}" style="background: #2563eb; color: #fff; padding: 10px 18px; border-radius: 4px; text-decoration: none; font-weight: 600;">Join Meeting</a>\n' +
      '  </div>\n' +
      '  <p>Best regards,<br>{{ sender_name }}<br>{{ sender_department }} &bull; {{ company_name }}</p>\n' +
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
        setSuccessMsg(`Template '${formName}' saved successfully.`)
        setShowEditorModal(false)
        fetchTemplates()
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
        fetchTemplates()
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
        fetchTemplates()
      } else {
        const err = await res.json()
        setErrorMsg(err.detail || 'Error deleting template')
      }
    } catch (e: any) {
      setErrorMsg(e.message)
    }
  }

  async function triggerPreview(subjectToTest?: string, bodyToTest?: string) {
    setPreviewLoading(true)
    setPreviewResult(null)

    const subj = subjectToTest !== undefined ? subjectToTest : (currentTemplate ? currentTemplate.subject : formSubject)
    const bod = bodyToTest !== undefined ? bodyToTest : (currentTemplate ? currentTemplate.body : formBody)

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

  function openPreviewForTemplate(tmpl: EmailTemplate) {
    setCurrentTemplate(tmpl)
    setShowPreviewModal(true)
    triggerPreview(tmpl.subject, tmpl.body)
  }

  function insertVariable(tag: string) {
    if (activeTargetField === 'subject') {
      setFormSubject(prev => prev + ' ' + tag)
    } else {
      setFormBody(prev => prev + '\n' + tag)
    }
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '32px 20px', fontFamily: 'system-ui, -apple-system, sans-serif', color: '#0f172a' }}>
      
      {/* Top Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28, borderBottom: '1px solid #e2e8f0', paddingBottom: 20 }}>
        <div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 4 }}>
            <a href="/" style={{ color: '#64748b', textDecoration: 'none', fontSize: 13 }}>Home</a>
            <span style={{ color: '#cbd5e1' }}>/</span>
            <a href="/employees" style={{ color: '#64748b', textDecoration: 'none', fontSize: 13 }}>Workforce</a>
            <span style={{ color: '#cbd5e1' }}>/</span>
            <span style={{ fontSize: 13, fontWeight: 600 }}>Templates</span>
          </div>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0, color: '#0f172a' }}>Email Template Studio</h1>
          <p style={{ color: '#64748b', margin: '4px 0 0 0', fontSize: 14 }}>
            Design, personalize, and preview reusable notification templates with Jinja2 sandboxing
          </p>
        </div>

        <button
          onClick={openCreateModal}
          style={{ backgroundColor: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, padding: '10px 18px', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
        >
          + Create New Template
        </button>
      </header>

      {/* Notices */}
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

      {/* Metric Bar */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '16px 20px' }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>Total Active Templates</span>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#0f172a', marginTop: 4 }}>{templates.length}</div>
        </div>
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '16px 20px' }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: '#2563eb', textTransform: 'uppercase' }}>Supported Variables</span>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb', marginTop: 4 }}>15</div>
        </div>
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '16px 20px' }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: '#059669', textTransform: 'uppercase' }}>Security Engine</span>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#059669', marginTop: 8 }}>Jinja2 Sandboxed</div>
        </div>
      </section>

      {/* Search & Category Pills */}
      <section style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          type="text"
          placeholder="Search templates by title or subject..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{ flex: 1, minWidth: 260, padding: '9px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13 }}
        />

        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          style={{ padding: '9px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13, background: '#fff' }}
        >
          {CATEGORIES.map(c => (
            <option key={c} value={c}>{c === 'All' ? 'All Categories' : c}</option>
          ))}
        </select>
      </section>

      {/* Templates Table */}
      <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 13 }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
              <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569' }}>Template Title</th>
              <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569' }}>Category</th>
              <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569' }}>Default Subject Line</th>
              <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569' }}>Last Updated</th>
              <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} style={{ padding: 32, textAlign: 'center', color: '#64748b' }}>
                  Loading templates...
                </td>
              </tr>
            ) : templates.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: 36, textAlign: 'center', color: '#94a3b8' }}>
                  No email templates found matching your search.
                </td>
              </tr>
            ) : (
              templates.map((t) => (
                <tr key={t.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={{ padding: '12px 16px', fontWeight: 600, color: '#0f172a' }}>
                    {t.template_name}
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <span style={{ display: 'inline-block', padding: '2px 8px', background: '#f1f5f9', color: '#334155', borderRadius: 4, fontSize: 11, fontWeight: 600 }}>
                      {t.category}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px', color: '#475569', maxWidth: 360, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <code>{t.subject}</code>
                  </td>
                  <td style={{ padding: '12px 16px', color: '#64748b', fontSize: 12 }}>
                    {t.updated_at ? new Date(t.updated_at).toLocaleDateString() : 'N/A'}
                  </td>
                  <td style={{ padding: '12px 16px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                    <button
                      onClick={() => openPreviewForTemplate(t)}
                      style={{ background: 'none', border: 'none', color: '#059669', cursor: 'pointer', fontWeight: 600, marginRight: 12, fontSize: 12 }}
                    >
                      Preview
                    </button>
                    <button
                      onClick={() => openEditModal(t)}
                      style={{ background: 'none', border: 'none', color: '#2563eb', cursor: 'pointer', fontWeight: 600, marginRight: 12, fontSize: 12 }}
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDuplicate(t)}
                      style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontWeight: 600, marginRight: 12, fontSize: 12 }}
                    >
                      Duplicate
                    </button>
                    <button
                      onClick={() => openDeleteModal(t)}
                      style={{ background: 'none', border: 'none', color: '#dc2626', cursor: 'pointer', fontWeight: 600, fontSize: 12 }}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* TEMPLATE EDITOR MODAL */}
      {showEditorModal && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50, padding: 20 }}>
          <div style={{ background: '#fff', borderRadius: 8, padding: 28, maxWidth: 960, width: '100%', maxHeight: '90vh', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e2e8f0', paddingBottom: 12 }}>
              <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>
                {currentTemplate ? `Edit Template: ${currentTemplate.template_name}` : 'Create New Email Template'}
              </h2>
              <button onClick={() => setShowEditorModal(false)} style={{ background: 'none', border: 'none', fontSize: 18, cursor: 'pointer' }}>&times;</button>
            </div>

            <form onSubmit={handleSaveTemplate} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Template Name *</label>
                  <input
                    required
                    placeholder="e.g. Quarterly Appraisal Notification"
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    style={{ width: '100%', padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 4, boxSizing: 'border-box' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Category *</label>
                  <select
                    value={formCategory}
                    onChange={(e) => setFormCategory(e.target.value)}
                    style={{ width: '100%', padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 4, background: '#fff', boxSizing: 'border-box' }}
                  >
                    {CATEGORIES.filter(c => c !== 'All').map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
                  Subject Line Template *
                  <span style={{ fontSize: 11, fontWeight: 400, color: '#64748b', marginLeft: 8 }}>(Supports variable tags)</span>
                </label>
                <input
                  required
                  placeholder="e.g. Action Required: {{ event_name }} - {{ name }}"
                  value={formSubject}
                  onFocus={() => setActiveTargetField('subject')}
                  onChange={(e) => setFormSubject(e.target.value)}
                  style={{ width: '100%', padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 4, boxSizing: 'border-box' }}
                />
              </div>

              {/* Variable Reference Insert Panel */}
              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 6, padding: '12px 14px' }}>
                <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#475569', letterSpacing: 0.5 }}>
                  Click to Insert Personalization Tag into Active Field ({activeTargetField === 'subject' ? 'Subject' : 'Body'}):
                </span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
                  {VARIABLE_PANEL.map(group => (
                    <div key={group.group} style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                      <span style={{ fontSize: 11, fontWeight: 600, color: '#64748b', minWidth: 120 }}>{group.group}:</span>
                      {group.vars.map(v => (
                        <button
                          key={v.tag}
                          type="button"
                          onClick={() => insertVariable(v.tag)}
                          style={{
                            background: '#fff',
                            border: '1px solid #cbd5e1',
                            borderRadius: 4,
                            padding: '3px 8px',
                            fontSize: 11,
                            fontFamily: 'monospace',
                            cursor: 'pointer',
                            color: '#1e40af'
                          }}
                          title={`Inserts ${v.tag} (${v.label})`}
                        >
                          + {v.tag}
                        </button>
                      ))}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
                  Email Body Template (HTML / Jinja2) *
                </label>
                <textarea
                  required
                  rows={10}
                  onFocus={() => setActiveTargetField('body')}
                  value={formBody}
                  onChange={(e) => setFormBody(e.target.value)}
                  style={{ width: '100%', padding: '10px', fontFamily: 'monospace', fontSize: 12, border: '1px solid #cbd5e1', borderRadius: 4, boxSizing: 'border-box' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10 }}>
                <button
                  type="button"
                  onClick={() => {
                    setShowPreviewModal(true)
                    triggerPreview(formSubject, formBody)
                  }}
                  style={{ background: '#f1f5f9', border: '1px solid #cbd5e1', padding: '8px 16px', borderRadius: 4, cursor: 'pointer', fontWeight: 600, fontSize: 13 }}
                >
                  Test &amp; Preview
                </button>

                <div style={{ display: 'flex', gap: 10 }}>
                  <button
                    type="button"
                    onClick={() => setShowEditorModal(false)}
                    style={{ background: '#f1f5f9', border: 'none', padding: '8px 16px', borderRadius: 4, cursor: 'pointer', fontWeight: 600, fontSize: 13 }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    style={{ background: '#2563eb', color: '#fff', border: 'none', padding: '8px 20px', borderRadius: 4, cursor: 'pointer', fontWeight: 600, fontSize: 13 }}
                  >
                    Save Template
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* LIVE PREVIEW MODAL */}
      {showPreviewModal && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 60, padding: 20 }}>
          <div style={{ background: '#fff', borderRadius: 8, padding: 28, maxWidth: 840, width: '100%', maxHeight: '90vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e2e8f0', paddingBottom: 12, marginBottom: 16 }}>
              <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>Real-Time Email Render Preview</h2>
              <button onClick={() => setShowPreviewModal(false)} style={{ background: 'none', border: 'none', fontSize: 18, cursor: 'pointer' }}>&times;</button>
            </div>

            {/* Recipient context selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, background: '#f8fafc', padding: '10px 14px', borderRadius: 6 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#475569' }}>Preview with Employee:</label>
              <select
                value={previewEmployeeId || ''}
                onChange={(e) => {
                  const eid = Number(e.target.value)
                  setPreviewEmployeeId(eid)
                  triggerPreview()
                }}
                style={{ padding: '6px 10px', borderRadius: 4, border: '1px solid #cbd5e1', fontSize: 13, background: '#fff' }}
              >
                {employees.map(emp => (
                  <option key={emp.id} value={emp.id}>
                    {emp.full_name} ({emp.employee_id} - {emp.department})
                  </option>
                ))}
              </select>

              <button
                onClick={() => triggerPreview()}
                style={{ background: '#0f172a', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: 4, fontSize: 12, cursor: 'pointer' }}
              >
                Re-render
              </button>
            </div>

            {/* Validation Notice */}
            {previewResult && !previewResult.is_valid && (
              <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 6, padding: '10px 14px', color: '#991b1b', fontSize: 13, marginBottom: 16 }}>
                <strong>Validation Error:</strong> {previewResult.validation_error}
              </div>
            )}

            {/* Subject Banner */}
            {previewResult && (
              <div style={{ border: '1px solid #e2e8f0', borderRadius: 6, padding: '10px 14px', background: '#f8fafc', marginBottom: 16 }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: '#64748b' }}>SUBJECT LINE:</span>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#0f172a', marginTop: 2 }}>{previewResult.rendered_subject}</div>
              </div>
            )}

            {/* Dual Tabs: HTML vs Plain Text */}
            <div style={{ display: 'flex', gap: 8, borderBottom: '1px solid #e2e8f0', marginBottom: 12 }}>
              <button
                onClick={() => setPreviewTab('html')}
                style={{
                  padding: '8px 14px',
                  background: 'none',
                  border: 'none',
                  borderBottom: previewTab === 'html' ? '2px solid #2563eb' : '2px solid transparent',
                  fontWeight: 600,
                  fontSize: 13,
                  color: previewTab === 'html' ? '#2563eb' : '#64748b',
                  cursor: 'pointer'
                }}
              >
                Rendered HTML Output
              </button>
              <button
                onClick={() => setPreviewTab('text')}
                style={{
                  padding: '8px 14px',
                  background: 'none',
                  border: 'none',
                  borderBottom: previewTab === 'text' ? '2px solid #2563eb' : '2px solid transparent',
                  fontWeight: 600,
                  fontSize: 13,
                  color: previewTab === 'text' ? '#2563eb' : '#64748b',
                  cursor: 'pointer'
                }}
              >
                Plain-Text Fallback
              </button>
            </div>

            {previewLoading ? (
              <div style={{ padding: 40, textAlign: 'center', color: '#64748b' }}>Rendering template...</div>
            ) : previewResult ? (
              previewTab === 'html' ? (
                <div
                  style={{ border: '1px solid #e2e8f0', borderRadius: 6, padding: 20, minHeight: 260, background: '#fff' }}
                  dangerouslySetInnerHTML={{ __html: previewResult.rendered_html }}
                />
              ) : (
                <pre style={{ border: '1px solid #e2e8f0', borderRadius: 6, padding: 16, background: '#f8fafc', whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: 12, color: '#334155', minHeight: 200 }}>
                  {previewResult.plain_text_fallback}
                </pre>
              )
            ) : null}

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 20 }}>
              <button
                onClick={() => setShowPreviewModal(false)}
                style={{ background: '#0f172a', color: '#fff', border: 'none', padding: '8px 18px', borderRadius: 4, cursor: 'pointer', fontWeight: 600 }}
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* DELETE CONFIRMATION MODAL */}
      {showDeleteModal && currentTemplate && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 60 }}>
          <div style={{ background: '#fff', borderRadius: 8, padding: 24, maxWidth: 440, width: '90%' }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: 16, color: '#991b1b' }}>Delete Email Template?</h3>
            <p style={{ fontSize: 13, color: '#475569', lineHeight: 1.5 }}>
              Are you sure you want to permanently delete template <strong>{currentTemplate.template_name}</strong>? Templates currently linked to campaigns cannot be deleted.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 20 }}>
              <button
                onClick={() => setShowDeleteModal(false)}
                style={{ background: '#f1f5f9', border: 'none', padding: '8px 14px', borderRadius: 4, cursor: 'pointer', fontWeight: 600 }}
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                style={{ background: '#dc2626', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 4, cursor: 'pointer', fontWeight: 600 }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}
