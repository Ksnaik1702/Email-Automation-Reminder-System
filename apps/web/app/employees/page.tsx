'use client'

import React, { useState, useEffect } from 'react'

interface Employee {
  id: number
  employee_id: string
  full_name: string
  email: string
  company: string
  department: string
  designation: string
  timezone: string
  employment_status: string
  created_at: string
  updated_at: string
}

interface Stats {
  total_employees: number
  active_employees: number
  inactive_employees: number
  departments_count: number
  department_distribution: Record<string, number>
}

interface ImportSummary {
  total_rows: number
  successfully_imported: number
  skipped_records: number
  failed_records: number
  errors: Array<{
    row_number: number
    employee_id?: string
    email?: string
    reason: string
  }>
}

export default function EmployeeManagementPage() {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

  const [employees, setEmployees] = useState<Employee[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [departments, setDepartments] = useState<string[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [errorMsg, setErrorMsg] = useState<string>('')
  const [successMsg, setSuccessMsg] = useState<string>('')

  // Search & Filters
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [selectedDept, setSelectedDept] = useState<string>('All')
  const [selectedStatus, setSelectedStatus] = useState<string>('All')

  // Modals
  const [showAddModal, setShowAddModal] = useState<boolean>(false)
  const [showEditModal, setShowEditModal] = useState<boolean>(false)
  const [showDeleteModal, setShowDeleteModal] = useState<boolean>(false)
  const [showImportModal, setShowImportModal] = useState<boolean>(false)
  const [currentEmployee, setCurrentEmployee] = useState<Employee | null>(null)

  // Form State
  const [formData, setFormData] = useState({
    employee_id: '',
    full_name: '',
    email: '',
    company: 'Nexus Tech',
    department: 'Operations',
    designation: 'Associate',
    timezone: 'Asia/Kolkata',
    employment_status: 'Active'
  })

  // Import Summary
  const [importSummary, setImportSummary] = useState<ImportSummary | null>(null)
  const [importing, setImporting] = useState<boolean>(false)

  useEffect(() => {
    fetchStats()
    fetchDepartments()
    fetchEmployees()
  }, [searchTerm, selectedDept, selectedStatus])

  async function fetchStats() {
    try {
      const res = await fetch(`${API_URL}/api/employees/stats`)
      if (res.ok) {
        setStats(await res.json())
      }
    } catch (e) {
      console.error('Failed to load stats:', e)
    }
  }

  async function fetchDepartments() {
    try {
      const res = await fetch(`${API_URL}/api/employees/departments`)
      if (res.ok) {
        setDepartments(await res.json())
      }
    } catch (e) {
      console.error('Failed to load departments:', e)
    }
  }

  async function fetchEmployees() {
    setLoading(true)
    setErrorMsg('')
    try {
      const params = new URLSearchParams()
      if (searchTerm.trim()) params.append('search', searchTerm.trim())
      if (selectedDept !== 'All') params.append('department', selectedDept)
      if (selectedStatus !== 'All') params.append('status', selectedStatus)

      const res = await fetch(`${API_URL}/api/employees?${params.toString()}`)
      if (res.ok) {
        const data = await res.json()
        setEmployees(data.items || [])
      } else {
        const err = await res.json()
        setErrorMsg(err.detail || 'Failed to fetch employee records')
      }
    } catch (e: any) {
      setErrorMsg(`API connection error: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setErrorMsg('')
    setSuccessMsg('')
    try {
      const res = await fetch(`${API_URL}/api/employees`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })

      if (res.ok) {
        setSuccessMsg(`Employee ${formData.full_name} (${formData.employee_id}) created successfully.`)
        setShowAddModal(false)
        resetForm()
        fetchEmployees()
        fetchStats()
        fetchDepartments()
      } else {
        const err = await res.json()
        setErrorMsg(err.detail || 'Validation error creating employee')
      }
    } catch (e: any) {
      setErrorMsg(e.message)
    }
  }

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault()
    if (!currentEmployee) return
    setErrorMsg('')
    setSuccessMsg('')
    try {
      const res = await fetch(`${API_URL}/api/employees/${currentEmployee.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: formData.full_name,
          email: formData.email,
          company: formData.company,
          department: formData.department,
          designation: formData.designation,
          timezone: formData.timezone,
          employment_status: formData.employment_status
        })
      })

      if (res.ok) {
        setSuccessMsg(`Employee ${formData.employee_id} updated successfully.`)
        setShowEditModal(false)
        setCurrentEmployee(null)
        fetchEmployees()
        fetchStats()
      } else {
        const err = await res.json()
        setErrorMsg(err.detail || 'Validation error updating employee')
      }
    } catch (e: any) {
      setErrorMsg(e.message)
    }
  }

  async function handleDelete() {
    if (!currentEmployee) return
    setErrorMsg('')
    setSuccessMsg('')
    try {
      const res = await fetch(`${API_URL}/api/employees/${currentEmployee.id}`, {
        method: 'DELETE'
      })

      if (res.ok) {
        setSuccessMsg(`Employee ${currentEmployee.full_name} (${currentEmployee.employee_id}) removed.`)
        setShowDeleteModal(false)
        setCurrentEmployee(null)
        fetchEmployees()
        fetchStats()
        fetchDepartments()
      } else {
        const err = await res.json()
        setErrorMsg(err.detail || 'Error deleting employee')
      }
    } catch (e: any) {
      setErrorMsg(e.message)
    }
  }

  function openEdit(emp: Employee) {
    setCurrentEmployee(emp)
    setFormData({
      employee_id: emp.employee_id,
      full_name: emp.full_name,
      email: emp.email,
      company: emp.company || '',
      department: emp.department || '',
      designation: emp.designation || '',
      timezone: emp.timezone || 'Asia/Kolkata',
      employment_status: emp.employment_status || 'Active'
    })
    setShowEditModal(true)
  }

  function openDelete(emp: Employee) {
    setCurrentEmployee(emp)
    setShowDeleteModal(true)
  }

  function resetForm() {
    setFormData({
      employee_id: '',
      full_name: '',
      email: '',
      company: 'Nexus Tech',
      department: 'Operations',
      designation: 'Associate',
      timezone: 'Asia/Kolkata',
      employment_status: 'Active'
    })
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    setImporting(true)
    setImportSummary(null)
    setErrorMsg('')

    const uploadData = new FormData()
    uploadData.append('file', file)

    try {
      const res = await fetch(`${API_URL}/api/employees/import-csv`, {
        method: 'POST',
        body: uploadData
      })

      if (res.ok) {
        const summary: ImportSummary = await res.json()
        setImportSummary(summary)
        fetchEmployees()
        fetchStats()
        fetchDepartments()
      } else {
        const err = await res.json()
        setErrorMsg(err.detail || 'CSV upload failed')
      }
    } catch (e: any) {
      setErrorMsg(`Upload failed: ${e.message}`)
    } finally {
      setImporting(false)
    }
  }

  function handleExport() {
    const params = new URLSearchParams()
    if (searchTerm.trim()) params.append('search', searchTerm.trim())
    if (selectedDept !== 'All') params.append('department', selectedDept)
    window.location.href = `${API_URL}/api/employees/export-csv?${params.toString()}`
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '32px 20px', fontFamily: 'system-ui, -apple-system, sans-serif', color: '#0f172a' }}>
      
      {/* Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28, borderBottom: '1px solid #e2e8f0', paddingBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0, color: '#0f172a' }}>Employee Directory</h1>
          <p style={{ color: '#64748b', margin: '4px 0 0 0', fontSize: 14 }}>
            Centralized corporate workforce database and recipient synchronization engine
          </p>
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={() => { resetForm(); setShowAddModal(true); }}
            style={{ backgroundColor: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, padding: '9px 16px', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
          >
            + Add Employee
          </button>
          <button
            onClick={() => { setImportSummary(null); setShowImportModal(true); }}
            style={{ backgroundColor: '#0f172a', color: '#fff', border: 'none', borderRadius: 6, padding: '9px 16px', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
          >
            Import CSV
          </button>
          <button
            onClick={handleExport}
            style={{ backgroundColor: '#fff', color: '#0f172a', border: '1px solid #cbd5e1', borderRadius: 6, padding: '9px 16px', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
          >
            Export CSV
          </button>
        </div>
      </header>

      {/* Alert Notices */}
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

      {/* Metrics Cards */}
      {stats && (
        <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginBottom: 28 }}>
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '16px 20px' }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>Total Workforce</span>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#0f172a', marginTop: 4 }}>{stats.total_employees}</div>
          </div>
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '16px 20px' }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#16a34a', textTransform: 'uppercase' }}>Active Employees</span>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#16a34a', marginTop: 4 }}>{stats.active_employees}</div>
          </div>
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '16px 20px' }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#dc2626', textTransform: 'uppercase' }}>Inactive / Leave</span>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#dc2626', marginTop: 4 }}>{stats.inactive_employees}</div>
          </div>
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '16px 20px' }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#2563eb', textTransform: 'uppercase' }}>Departments</span>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb', marginTop: 4 }}>{stats.departments_count}</div>
          </div>
        </section>
      )}

      {/* Filter and Search Bar */}
      <section style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          type="text"
          placeholder="Search by name, ID, or email..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{ flex: 1, minWidth: 260, padding: '9px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13 }}
        />

        <select
          value={selectedDept}
          onChange={(e) => setSelectedDept(e.target.value)}
          style={{ padding: '9px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13, background: '#fff' }}
        >
          <option value="All">All Departments</option>
          {departments.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>

        <select
          value={selectedStatus}
          onChange={(e) => setSelectedStatus(e.target.value)}
          style={{ padding: '9px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13, background: '#fff' }}
        >
          <option value="All">All Statuses</option>
          <option value="Active">Active</option>
          <option value="Inactive">Inactive</option>
          <option value="On Leave">On Leave</option>
          <option value="Terminated">Terminated</option>
        </select>
      </section>

      {/* Employee Data Table */}
      <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 13 }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
              <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569' }}>Employee Code</th>
              <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569' }}>Full Name</th>
              <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569' }}>Email Address</th>
              <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569' }}>Department</th>
              <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569' }}>Designation</th>
              <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569' }}>Status</th>
              <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ padding: 32, textAlign: 'center', color: '#64748b' }}>
                  Loading workforce data...
                </td>
              </tr>
            ) : employees.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: 36, textAlign: 'center', color: '#94a3b8' }}>
                  No employee records matched your filter criteria.
                </td>
              </tr>
            ) : (
              employees.map((emp) => (
                <tr key={emp.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={{ padding: '12px 16px', fontFamily: 'monospace', fontWeight: 600, color: '#1e293b' }}>
                    {emp.employee_id}
                  </td>
                  <td style={{ padding: '12px 16px', fontWeight: 500 }}>
                    {emp.full_name}
                  </td>
                  <td style={{ padding: '12px 16px', color: '#475569' }}>
                    {emp.email}
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <span style={{ display: 'inline-block', padding: '2px 8px', background: '#f1f5f9', borderRadius: 4, fontSize: 11, fontWeight: 500 }}>
                      {emp.department || 'N/A'}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px', color: '#475569' }}>
                    {emp.designation || 'Staff'}
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <span style={{
                      display: 'inline-block',
                      padding: '2px 8px',
                      borderRadius: 12,
                      fontSize: 11,
                      fontWeight: 600,
                      background: emp.employment_status === 'Active' ? '#dcfce7' : '#fee2e2',
                      color: emp.employment_status === 'Active' ? '#15803d' : '#b91c1c'
                    }}>
                      {emp.employment_status}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                    <button
                      onClick={() => openEdit(emp)}
                      style={{ background: 'none', border: 'none', color: '#2563eb', cursor: 'pointer', fontWeight: 600, marginRight: 12, fontSize: 12 }}
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => openDelete(emp)}
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

      {/* ADD EMPLOYEE MODAL */}
      {showAddModal && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
          <div style={{ background: '#fff', borderRadius: 8, padding: 28, maxWidth: 520, width: '90%', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)' }}>
            <h2 style={{ margin: '0 0 16px 0', fontSize: 18, fontWeight: 700 }}>Add New Employee</h2>
            <form onSubmit={handleCreate}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Employee Code *</label>
                  <input
                    required
                    placeholder="e.g. EMP-101"
                    value={formData.employee_id}
                    onChange={(e) => setFormData({ ...formData, employee_id: e.target.value })}
                    style={{ width: '100%', padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 4, boxSizing: 'border-box' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Full Name *</label>
                  <input
                    required
                    placeholder="e.g. Priya Patel"
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                    style={{ width: '100%', padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 4, boxSizing: 'border-box' }}
                  />
                </div>
              </div>

              <div style={{ marginBottom: 12 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Corporate Email *</label>
                <input
                  required
                  type="email"
                  placeholder="name@company.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 4, boxSizing: 'border-box' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Department</label>
                  <input
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    style={{ width: '100%', padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 4, boxSizing: 'border-box' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Designation</label>
                  <input
                    value={formData.designation}
                    onChange={(e) => setFormData({ ...formData, designation: e.target.value })}
                    style={{ width: '100%', padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 4, boxSizing: 'border-box' }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Timezone</label>
                  <input
                    value={formData.timezone}
                    onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                    style={{ width: '100%', padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 4, boxSizing: 'border-box' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Status</label>
                  <select
                    value={formData.employment_status}
                    onChange={(e) => setFormData({ ...formData, employment_status: e.target.value })}
                    style={{ width: '100%', padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 4, background: '#fff', boxSizing: 'border-box' }}
                  >
                    <option value="Active">Active</option>
                    <option value="Inactive">Inactive</option>
                    <option value="On Leave">On Leave</option>
                    <option value="Terminated">Terminated</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  style={{ background: '#f1f5f9', border: 'none', padding: '8px 14px', borderRadius: 4, cursor: 'pointer', fontWeight: 600 }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{ background: '#2563eb', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 4, cursor: 'pointer', fontWeight: 600 }}
                >
                  Save Employee
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT MODAL */}
      {showEditModal && currentEmployee && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
          <div style={{ background: '#fff', borderRadius: 8, padding: 28, maxWidth: 520, width: '90%' }}>
            <h2 style={{ margin: '0 0 16px 0', fontSize: 18, fontWeight: 700 }}>Edit Employee ({currentEmployee.employee_id})</h2>
            <form onSubmit={handleUpdate}>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Full Name</label>
                <input
                  required
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 4, boxSizing: 'border-box' }}
                />
              </div>

              <div style={{ marginBottom: 12 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Email Address</label>
                <input
                  required
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 4, boxSizing: 'border-box' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Department</label>
                  <input
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    style={{ width: '100%', padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 4, boxSizing: 'border-box' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Designation</label>
                  <input
                    value={formData.designation}
                    onChange={(e) => setFormData({ ...formData, designation: e.target.value })}
                    style={{ width: '100%', padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 4, boxSizing: 'border-box' }}
                  />
                </div>
              </div>

              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Status</label>
                <select
                  value={formData.employment_status}
                  onChange={(e) => setFormData({ ...formData, employment_status: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 4, background: '#fff', boxSizing: 'border-box' }}
                >
                  <option value="Active">Active</option>
                  <option value="Inactive">Inactive</option>
                  <option value="On Leave">On Leave</option>
                  <option value="Terminated">Terminated</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  style={{ background: '#f1f5f9', border: 'none', padding: '8px 14px', borderRadius: 4, cursor: 'pointer', fontWeight: 600 }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{ background: '#2563eb', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 4, cursor: 'pointer', fontWeight: 600 }}
                >
                  Update
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DELETE CONFIRMATION MODAL */}
      {showDeleteModal && currentEmployee && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
          <div style={{ background: '#fff', borderRadius: 8, padding: 24, maxWidth: 440, width: '90%' }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: 16, color: '#991b1b' }}>Confirm Deletion</h3>
            <p style={{ fontSize: 13, color: '#475569', lineHeight: 1.5 }}>
              Are you sure you want to delete employee <strong>{currentEmployee.full_name}</strong> ({currentEmployee.employee_id})? This action will cascade to associated scheduled reminders.
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
                Delete Permanently
              </button>
            </div>
          </div>
        </div>
      )}

      {/* CSV IMPORT MODAL */}
      {showImportModal && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
          <div style={{ background: '#fff', borderRadius: 8, padding: 28, maxWidth: 640, width: '90%', maxHeight: '85vh', overflowY: 'auto' }}>
            <h2 style={{ margin: '0 0 8px 0', fontSize: 18, fontWeight: 700 }}>Bulk Ingest Employees via CSV</h2>
            <p style={{ fontSize: 13, color: '#64748b', margin: '0 0 18px 0' }}>
              Upload a comma-separated file with headers: <code>employee_id</code>, <code>full_name</code>, <code>email</code>, <code>department</code>, <code>designation</code>.
            </p>

            <input
              type="file"
              accept=".csv"
              onChange={handleFileUpload}
              disabled={importing}
              style={{ display: 'block', width: '100%', padding: '12px', border: '2px dashed #cbd5e1', borderRadius: 6, marginBottom: 18 }}
            />

            {importing && <p style={{ fontSize: 13, color: '#2563eb' }}>Processing records and validating constraints...</p>}

            {/* Summary */}
            {importSummary && (
              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 6, padding: 16, marginBottom: 16 }}>
                <h4 style={{ margin: '0 0 8px 0', fontSize: 14 }}>Import Audit Summary</h4>
                <div style={{ display: 'flex', gap: 16, fontSize: 13, marginBottom: 12 }}>
                  <div>Total Processed: <strong>{importSummary.total_rows}</strong></div>
                  <div style={{ color: '#16a34a' }}>Successfully Added: <strong>{importSummary.successfully_imported}</strong></div>
                  <div style={{ color: '#d97706' }}>Skipped (Duplicates): <strong>{importSummary.skipped_records}</strong></div>
                  <div style={{ color: '#dc2626' }}>Failed: <strong>{importSummary.failed_records}</strong></div>
                </div>

                {importSummary.errors.length > 0 && (
                  <div style={{ marginTop: 10 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#991b1b', marginBottom: 4 }}>Error &amp; Skip Diagnostics:</div>
                    <ul style={{ maxHeight: 160, overflowY: 'auto', paddingLeft: 18, fontSize: 12, color: '#475569', margin: 0 }}>
                      {importSummary.errors.map((err, i) => (
                        <li key={i} style={{ marginBottom: 4 }}>
                          Row {err.row_number} [{err.employee_id || 'N/A'}]: {err.reason}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button
                onClick={() => setShowImportModal(false)}
                style={{ background: '#0f172a', color: '#fff', border: 'none', padding: '8px 18px', borderRadius: 4, cursor: 'pointer', fontWeight: 600 }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}
