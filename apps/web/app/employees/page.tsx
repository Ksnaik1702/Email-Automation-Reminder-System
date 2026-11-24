'use client'

import React, { useState, useEffect } from 'react'
import AppLayout from '../../components/AppLayout'
import KPICard from '../../components/KPICard'
import StatusBadge from '../../components/StatusBadge'
import Button from '../../components/Button'
import SearchInput from '../../components/SearchInput'
import Modal from '../../components/Modal'
import EmptyState from '../../components/EmptyState'
import {
  Users,
  UserCheck,
  UserX,
  Building2,
  Plus,
  Upload,
  Download,
  Edit,
  Trash2,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
  AlertTriangle,
  Mail,
  Briefcase,
  Globe
} from 'lucide-react'

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
    employment_status: 'Active',
  })

  // Import State
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
        body: JSON.stringify(formData),
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
          employment_status: formData.employment_status,
        }),
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
        method: 'DELETE',
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
      employment_status: emp.employment_status || 'Active',
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
      employment_status: 'Active',
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
        body: uploadData,
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
    <AppLayout
      title="Corporate Employee Directory"
      subtitle="Unified corporate workforce repository, targeting criteria, and employee records"
      breadcrumbs={[{ label: 'Employees' }]}
      actions={
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            icon={Download}
            onClick={handleExport}
          >
            Export CSV
          </Button>
          <Button
            variant="secondary"
            size="sm"
            icon={Upload}
            onClick={() => {
              setImportSummary(null)
              setShowImportModal(true)
            }}
          >
            Import CSV
          </Button>
          <Button
            variant="primary"
            size="sm"
            icon={Plus}
            onClick={() => {
              resetForm()
              setShowAddModal(true)
            }}
          >
            Add Employee
          </Button>
        </div>
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

      {/* 4 KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KPICard
          title="Total Employees"
          value={stats?.total_employees ?? 0}
          icon={Users}
          accent="indigo"
          subtitle="Corporate directory headcount"
          loading={loading && !stats}
        />
        <KPICard
          title="Active Employees"
          value={stats?.active_employees ?? 0}
          icon={UserCheck}
          accent="emerald"
          badge={
            stats && stats.total_employees > 0
              ? `${Math.round((stats.active_employees / stats.total_employees) * 100)}%`
              : '0%'
          }
          badgeType="success"
          subtitle="Eligible for notification campaigns"
          loading={loading && !stats}
        />
        <KPICard
          title="Inactive / Leave"
          value={stats?.inactive_employees ?? 0}
          icon={UserX}
          accent="amber"
          subtitle="Excluded by delivery safety filters"
          loading={loading && !stats}
        />
        <KPICard
          title="Departments"
          value={stats?.departments_count ?? departments.length}
          icon={Building2}
          accent="purple"
          subtitle="Active organizational units"
          loading={loading && !stats}
        />
      </div>

      {/* Filter & Search Toolbar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs mb-6">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <div className="flex-1 max-w-md">
            <SearchInput
              value={searchTerm}
              onChange={setSearchTerm}
              placeholder="Search by name, employee code, or email..."
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Department Filter */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-500 whitespace-nowrap">Dept:</span>
              <select
                value={selectedDept}
                onChange={(e) => setSelectedDept(e.target.value)}
                className="text-xs py-2 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none shadow-xs"
              >
                <option value="All">All Departments</option>
                {departments.map((dept) => (
                  <option key={dept} value={dept}>
                    {dept}
                  </option>
                ))}
              </select>
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-500 whitespace-nowrap">Status:</span>
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="text-xs py-2 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none shadow-xs"
              >
                <option value="All">All Statuses</option>
                <option value="Active">Active</option>
                <option value="Inactive">Inactive</option>
                <option value="On Leave">On Leave</option>
                <option value="Terminated">Terminated</option>
              </select>
            </div>

            {(searchTerm || selectedDept !== 'All' || selectedStatus !== 'All') && (
              <Button
                variant="ghost"
                size="sm"
                icon={RotateCcw}
                onClick={() => {
                  setSearchTerm('')
                  setSelectedDept('All')
                  setSelectedStatus('All')
                }}
              >
                Reset
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Main Employee Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        {loading && employees.length === 0 ? (
          <div className="p-12 text-center text-sm text-slate-400">
            Loading corporate workforce records...
          </div>
        ) : employees.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No employees found"
              description="No employee records match your search criteria or directory filters."
              icon={Users}
              actionLabel="Add New Employee"
              onAction={() => {
                resetForm()
                setShowAddModal(true)
              }}
              actionIcon={Plus}
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-[#F8FAFC] text-slate-600 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Code</th>
                  <th className="py-3 px-4">Full Name</th>
                  <th className="py-3 px-4">Corporate Email</th>
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-4">Designation</th>
                  <th className="py-3 px-4">Timezone</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {employees.map((emp) => {
                  const initials = emp.full_name
                    .split(' ')
                    .map((n) => n[0])
                    .join('')
                    .substring(0, 2)
                    .toUpperCase()

                  return (
                    <tr
                      key={emp.id}
                      className="hover:bg-slate-50/70 transition-colors group"
                    >
                      <td className="py-3.5 px-4 font-mono text-xs font-bold text-slate-700">
                        {emp.employee_id}
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 font-bold text-xs flex items-center justify-center flex-shrink-0">
                            {initials}
                          </div>
                          <div>
                            <p className="font-semibold text-slate-900 leading-tight">
                              {emp.full_name}
                            </p>
                            <p className="text-xs text-slate-400">{emp.company}</p>
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-slate-600 text-xs font-mono">
                        {emp.email}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
                          {emp.department || 'General'}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-xs text-slate-700">
                        {emp.designation || 'Staff'}
                      </td>
                      <td className="py-3.5 px-4 text-xs text-slate-500 font-mono">
                        {emp.timezone}
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <StatusBadge status={emp.employment_status} size="sm" />
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => openEdit(emp)}
                            title="Edit Employee"
                            className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => openDelete(emp)}
                            title="Delete Employee"
                            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Table Footer */}
        <div className="px-4 py-3 bg-slate-50/50 border-t border-slate-200 text-xs text-slate-500 flex items-center justify-between">
          <span>Showing {employees.length} workforce records</span>
          <span>Database: SQLite Unified Storage</span>
        </div>
      </div>

      {/* ADD EMPLOYEE MODAL */}
      <Modal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        title="Add New Employee"
        subtitle="Register a new employee record into the unified database"
        maxWidth="lg"
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Employee Code *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. EMP-105"
                value={formData.employee_id}
                onChange={(e) => setFormData({ ...formData, employee_id: e.target.value })}
                className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Full Name *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Priya Sharma"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Corporate Email Address *
            </label>
            <input
              type="email"
              required
              placeholder="e.g. priya.sharma@nexuscorp.com"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Company</label>
              <input
                type="text"
                value={formData.company}
                onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Department</label>
              <input
                type="text"
                value={formData.department}
                onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Designation</label>
              <input
                type="text"
                value={formData.designation}
                onChange={(e) => setFormData({ ...formData, designation: e.target.value })}
                className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Status</label>
              <select
                value={formData.employment_status}
                onChange={(e) => setFormData({ ...formData, employment_status: e.target.value })}
                className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              >
                <option value="Active">Active</option>
                <option value="Inactive">Inactive</option>
                <option value="On Leave">On Leave</option>
                <option value="Terminated">Terminated</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">IANA Timezone</label>
            <input
              type="text"
              value={formData.timezone}
              onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
              className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none font-mono"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="secondary" type="button" onClick={() => setShowAddModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit">
              Save Employee
            </Button>
          </div>
        </form>
      </Modal>

      {/* EDIT EMPLOYEE MODAL */}
      <Modal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        title="Edit Employee Record"
        subtitle={`Updating information for ${formData.full_name} (${formData.employee_id})`}
        maxWidth="lg"
      >
        <form onSubmit={handleUpdate} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Employee Code (Read-Only)
            </label>
            <input
              type="text"
              disabled
              value={formData.employee_id}
              className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg bg-slate-100 text-slate-500 cursor-not-allowed font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name *</label>
            <input
              type="text"
              required
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Corporate Email *
            </label>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Company</label>
              <input
                type="text"
                value={formData.company}
                onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Department</label>
              <input
                type="text"
                value={formData.department}
                onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Designation</label>
              <input
                type="text"
                value={formData.designation}
                onChange={(e) => setFormData({ ...formData, designation: e.target.value })}
                className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Status</label>
              <select
                value={formData.employment_status}
                onChange={(e) => setFormData({ ...formData, employment_status: e.target.value })}
                className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              >
                <option value="Active">Active</option>
                <option value="Inactive">Inactive</option>
                <option value="On Leave">On Leave</option>
                <option value="Terminated">Terminated</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">IANA Timezone</label>
            <input
              type="text"
              value={formData.timezone}
              onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
              className="w-full text-xs py-2 px-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none font-mono"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="secondary" type="button" onClick={() => setShowEditModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit">
              Update Employee
            </Button>
          </div>
        </form>
      </Modal>

      {/* DELETE CONFIRMATION MODAL */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Employee Record?"
        subtitle="This operation cannot be undone."
        maxWidth="md"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            Are you sure you want to permanently remove employee{' '}
            <strong className="text-slate-900">{currentEmployee?.full_name}</strong> (
            <span className="font-mono text-xs">{currentEmployee?.employee_id}</span>)?
          </p>
          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="secondary" onClick={() => setShowDeleteModal(false)}>
              Cancel
            </Button>
            <Button variant="danger" icon={Trash2} onClick={handleDelete}>
              Delete Record
            </Button>
          </div>
        </div>
      </Modal>

      {/* CSV IMPORT MODAL */}
      <Modal
        isOpen={showImportModal}
        onClose={() => setShowImportModal(false)}
        title="Import Employees via CSV"
        subtitle="Batch upload corporate records. Supported headers: employee_id, full_name, email, department, designation, timezone."
        maxWidth="xl"
      >
        <div className="space-y-5">
          <div className="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center bg-slate-50 hover:bg-slate-100/60 transition-colors cursor-pointer relative">
            <input
              type="file"
              accept=".csv"
              onChange={handleFileUpload}
              disabled={importing}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <div className="flex flex-col items-center">
              <FileSpreadsheet className="w-10 h-10 text-indigo-600 mb-2" />
              <p className="text-sm font-semibold text-slate-800">
                {importing ? 'Processing CSV Batch...' : 'Click or drag a CSV file here to upload'}
              </p>
              <p className="text-xs text-slate-400 mt-1">Maximum file size: 10MB</p>
            </div>
          </div>

          {/* Import Summary Results */}
          {importSummary && (
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-3">
              <h4 className="font-bold text-slate-900 text-sm">Import Audit Summary</h4>
              <div className="grid grid-cols-4 gap-2 text-center">
                <div className="bg-white p-2 rounded-lg border border-slate-200">
                  <div className="text-xs text-slate-500">Total Rows</div>
                  <div className="text-base font-bold text-slate-900">{importSummary.total_rows}</div>
                </div>
                <div className="bg-white p-2 rounded-lg border border-emerald-200 text-emerald-700">
                  <div className="text-xs">Imported</div>
                  <div className="text-base font-bold">{importSummary.successfully_imported}</div>
                </div>
                <div className="bg-white p-2 rounded-lg border border-amber-200 text-amber-700">
                  <div className="text-xs">Skipped</div>
                  <div className="text-base font-bold">{importSummary.skipped_records}</div>
                </div>
                <div className="bg-white p-2 rounded-lg border border-rose-200 text-rose-700">
                  <div className="text-xs">Failed</div>
                  <div className="text-base font-bold">{importSummary.failed_records}</div>
                </div>
              </div>

              {/* Errors List */}
              {importSummary.errors.length > 0 && (
                <div className="mt-3">
                  <p className="font-semibold text-rose-700 mb-1">Rejected Rows Detail:</p>
                  <div className="max-h-40 overflow-y-auto rounded-lg border border-rose-200 bg-rose-50/50 p-2 space-y-1">
                    {importSummary.errors.map((err, i) => (
                      <div key={i} className="text-[11px] text-rose-900 flex items-start gap-2">
                        <span className="font-mono font-bold">Row {err.row_number}:</span>
                        <span>{err.reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
            <Button variant="secondary" onClick={() => setShowImportModal(false)}>
              Close
            </Button>
          </div>
        </div>
      </Modal>
    </AppLayout>
  )
}
