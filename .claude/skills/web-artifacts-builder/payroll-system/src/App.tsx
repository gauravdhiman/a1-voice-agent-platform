import { useState, useEffect } from 'react'
import { LayoutDashboard, DollarSign, Users, Calendar, Settings, ChevronRight, TrendingUp, TrendingDown, CheckCircle2, Clock, AlertCircle, X, Plus } from 'lucide-react'
import { initDatabase, getEmployees, addEmployee as dbAddEmployee, getTotalPayroll, getActiveEmployeesCount, clearDatabase } from './db'

type Page = 'dashboard' | 'payroll' | 'employees'

interface StatCard {
  title: string
  value: string
  change: string
  trend: 'up' | 'down' | 'neutral'
  icon: React.ReactNode
}

interface PayrollRun {
  id: string
  period: string
  status: 'completed' | 'processing' | 'pending'
  amount: string
  date: string
}

interface Employee {
  id: string
  name: string
  email: string
  role: string
  department: string
  salary: number
  status: 'active' | 'inactive'
}

interface FormData {
  name: string
  email: string
  role: string
  department: string
  salary: string
  status: 'active' | 'inactive'
}

const departments = ['Engineering', 'Design', 'Product', 'Marketing', 'Sales', 'Human Resources', 'Finance', 'Operations', 'Analytics', 'Customer Support']

const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount)
}

const Dashboard = ({ totalPayroll, activeEmployeesCount }: { totalPayroll: number, activeEmployeesCount: number }) => {
  const stats: StatCard[] = [
    {
      title: 'Total Payroll',
      value: formatCurrency(totalPayroll),
      change: '+12.5%',
      trend: 'up',
      icon: <DollarSign className="h-5 w-5" />
    },
    {
      title: 'Active Employees',
      value: activeEmployeesCount.toString(),
      change: '+3',
      trend: 'up',
      icon: <Users className="h-5 w-5" />
    },
    {
      title: 'Pay Period',
      value: 'Dec 1-15',
      change: '5 days',
      trend: 'neutral',
      icon: <Calendar className="h-5 w-5" />
    },
    {
      title: 'Pending Approvals',
      value: '4',
      change: '-2',
      trend: 'down',
      icon: <AlertCircle className="h-5 w-5" />
    }
  ]

  const recentRuns: PayrollRun[] = [
    { id: '1', period: 'Nov 16-30', status: 'completed', amount: '$142,250', date: 'Dec 1' },
    { id: '2', period: 'Nov 1-15', status: 'completed', amount: '$142,250', date: 'Nov 16' },
    { id: '3', period: 'Oct 16-31', status: 'completed', amount: '$140,500', date: 'Nov 1' },
    { id: '4', period: 'Oct 1-15', status: 'completed', amount: '$138,750', date: 'Oct 16' }
  ]

  return (
    <div className="space-y-8 animate-in">
      <div>
        <h1 className="text-4xl font-bold mb-2">Dashboard</h1>
        <p className="text-muted-foreground">Overview of your payroll operations</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, idx) => (
          <div key={idx} className="bg-card border border-border rounded-lg p-6 hover-lift delay-100 animate-in">
            <div className="flex items-start justify-between mb-4">
              <div className="p-2 bg-primary/10 rounded-lg">
                {stat.icon}
              </div>
              <div className={`flex items-center text-sm ${stat.trend === 'up' ? 'text-green-600' : stat.trend === 'down' ? 'text-red-600' : 'text-muted-foreground'}`}>
                {stat.trend === 'up' ? <TrendingUp className="h-4 w-4 mr-1" /> : stat.trend === 'down' ? <TrendingDown className="h-4 w-4 mr-1" /> : <Clock className="h-4 w-4 mr-1" />}
                {stat.change}
              </div>
            </div>
            <div className="text-3xl font-bold mb-1">{stat.value}</div>
            <div className="text-sm text-muted-foreground">{stat.title}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-lg p-6 delay-300 animate-in">
          <h2 className="text-xl font-semibold mb-4">Recent Payroll Runs</h2>
          <div className="space-y-3">
            {recentRuns.map((run) => (
              <div key={run.id} className="flex items-center justify-between p-4 bg-muted/30 rounded-lg hover:bg-muted/50 transition-colors cursor-pointer">
                <div className="flex items-center gap-4">
                  <div className={`p-2 rounded-full ${run.status === 'completed' ? 'bg-green-100 text-green-700' : run.status === 'processing' ? 'bg-blue-100 text-blue-700' : 'bg-yellow-100 text-yellow-700'}`}>
                    {run.status === 'completed' ? <CheckCircle2 className="h-4 w-4" /> : <Clock className="h-4 w-4" />}
                  </div>
                  <div>
                    <div className="font-medium">{run.period}</div>
                    <div className="text-sm text-muted-foreground">{run.date}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-semibold">{run.amount}</div>
                  <div className="text-xs text-muted-foreground capitalize">{run.status}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-card border border-border rounded-lg p-6 delay-400 animate-in">
          <h2 className="text-xl font-semibold mb-4">Upcoming Actions</h2>
          <div className="space-y-4">
            <div className="p-4 bg-primary/5 border-l-4 border-primary rounded-r-lg">
              <div className="font-medium mb-1">Run Payroll for Dec 1-15</div>
              <div className="text-sm text-muted-foreground mb-2">Due in 5 days</div>
              <button className="text-sm font-medium text-primary hover:underline flex items-center gap-1">
                Review & Run <ChevronRight className="h-4 w-4" />
              </button>
            </div>
            <div className="p-4 bg-muted/30 border-l-4 border-muted rounded-r-lg">
              <div className="font-medium mb-1">Review Time Off Requests</div>
              <div className="text-sm text-muted-foreground mb-2">8 pending requests</div>
              <button className="text-sm font-medium text-primary hover:underline flex items-center gap-1">
                View Requests <ChevronRight className="h-4 w-4" />
              </button>
            </div>
            <div className="p-4 bg-muted/30 border-l-4 border-muted rounded-r-lg">
              <div className="font-medium mb-1">Update Tax Information</div>
              <div className="text-sm text-muted-foreground mb-2">Q4 2024 updates available</div>
              <button className="text-sm font-medium text-primary hover:underline flex items-center gap-1">
                Update Now <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const PayrollRuns = () => {
  const runs: PayrollRun[] = [
    { id: '1', period: 'Dec 1-15', status: 'pending', amount: '$142,500', date: 'Dec 16' },
    { id: '2', period: 'Nov 16-30', status: 'completed', amount: '$142,250', date: 'Dec 1' },
    { id: '3', period: 'Nov 1-15', status: 'completed', amount: '$142,250', date: 'Nov 16' },
    { id: '4', period: 'Oct 16-31', status: 'completed', amount: '$140,500', date: 'Nov 1' },
    { id: '5', period: 'Oct 1-15', status: 'completed', amount: '$138,750', date: 'Oct 16' },
    { id: '6', period: 'Sep 16-30', status: 'completed', amount: '$136,000', date: 'Oct 1' }
  ]

  return (
    <div className="space-y-6 animate-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold mb-2">Payroll Runs</h1>
          <p className="text-muted-foreground">Manage and track payroll processing</p>
        </div>
        <button className="px-6 py-2.5 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors">
          Run Payroll
        </button>
      </div>

      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/30 border-b border-border">
            <tr>
              <th className="text-left px-6 py-4 text-sm font-medium text-muted-foreground">Pay Period</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-muted-foreground">Status</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-muted-foreground">Total Amount</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-muted-foreground">Process Date</th>
              <th className="text-right px-6 py-4 text-sm font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {runs.map((run) => (
              <tr key={run.id} className="hover:bg-muted/20 transition-colors">
                <td className="px-6 py-4 font-medium">{run.period}</td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${run.status === 'completed' ? 'bg-green-100 text-green-700' : run.status === 'processing' ? 'bg-blue-100 text-blue-700' : 'bg-yellow-100 text-yellow-700'}`}>
                    {run.status === 'completed' ? <CheckCircle2 className="h-3 w-3" /> : <Clock className="h-3 w-3" />}
                    {run.status}
                  </span>
                </td>
                <td className="px-6 py-4 font-medium">{run.amount}</td>
                <td className="px-6 py-4 text-muted-foreground">{run.date}</td>
                <td className="px-6 py-4 text-right">
                  <button className="text-sm font-medium text-primary hover:underline">View</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const Employees = ({ employees, onAddEmployee }: { employees: Employee[], onAddEmployee: (employee: Omit<Employee, 'id'>) => Promise<void> }) => {
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [formData, setFormData] = useState<FormData>({
    name: '',
    email: '',
    role: '',
    department: '',
    salary: '',
    status: 'active'
  })
  const [errors, setErrors] = useState<Partial<Record<keyof FormData, string>>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  const validateForm = (): boolean => {
    const newErrors: Partial<Record<keyof FormData, string>> = {}

    if (!formData.name.trim()) {
      newErrors.name = 'Name is required'
    }

    if (!formData.email.trim()) {
      newErrors.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Invalid email format'
    }

    if (!formData.role.trim()) {
      newErrors.role = 'Role is required'
    }

    if (!formData.department) {
      newErrors.department = 'Department is required'
    }

    if (!formData.salary.trim()) {
      newErrors.salary = 'Salary is required'
    } else {
      const salaryNum = parseFloat(formData.salary.replace(/[^0-9.]/g, ''))
      if (isNaN(salaryNum) || salaryNum < 0) {
        newErrors.salary = 'Please enter a valid salary'
      }
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    setIsSubmitting(true)

    try {
      const salaryNum = parseFloat(formData.salary.replace(/[^0-9.]/g, ''))

      await onAddEmployee({
        name: formData.name.trim(),
        email: formData.email.trim(),
        role: formData.role.trim(),
        department: formData.department,
        salary: salaryNum,
        status: formData.status
      })

      setFormData({
        name: '',
        email: '',
        role: '',
        department: '',
        salary: '',
        status: 'active'
      })
      setErrors({})
      setShowAddDialog(false)
    } catch (error) {
      console.error('Failed to add employee:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSalaryChange = (value: string) => {
    const cleanValue = value.replace(/[^0-9.]/g, '')
    if (cleanValue === '') {
      setFormData({ ...formData, salary: '' })
      return
    }

    const parts = cleanValue.split('.')
    if (parts.length > 2) {
      return
    }

    const wholeNumber = parts[0] || '0'
    const decimal = parts[1] ? `.${parts[1].slice(0, 2)}` : ''

    setFormData({
      ...formData,
      salary: `${wholeNumber}${decimal}`
    })
  }

  return (
    <div className="space-y-6 animate-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold mb-2">Employees</h1>
          <p className="text-muted-foreground">Manage compensation and payroll details</p>
        </div>
        <button
          onClick={() => setShowAddDialog(true)}
          className="px-6 py-2.5 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Add Employee
        </button>
      </div>

      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/30 border-b border-border">
            <tr>
              <th className="text-left px-6 py-4 text-sm font-medium text-muted-foreground">Employee</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-muted-foreground">Email</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-muted-foreground">Role</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-muted-foreground">Department</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-muted-foreground">Annual Salary</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-muted-foreground">Status</th>
              <th className="text-right px-6 py-4 text-sm font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {employees.map((employee) => (
              <tr key={employee.id} className="hover:bg-muted/20 transition-colors cursor-pointer">
                <td className="px-6 py-4 font-medium">{employee.name}</td>
                <td className="px-6 py-4 text-muted-foreground">{employee.email}</td>
                <td className="px-6 py-4 text-muted-foreground">{employee.role}</td>
                <td className="px-6 py-4 text-muted-foreground">{employee.department}</td>
                <td className="px-6 py-4 font-medium">{formatCurrency(employee.salary)}</td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${employee.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'}`}>
                    {employee.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <button className="text-sm font-medium text-primary hover:underline">Details</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showAddDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50" onClick={() => setShowAddDialog(false)}>
          <div
            className="bg-card rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold">Add New Employee</h2>
                <button
                  onClick={() => setShowAddDialog(false)}
                  className="p-2 hover:bg-muted rounded-lg transition-colors"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Full Name *</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className={`w-full px-4 py-2.5 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 transition-colors ${errors.name ? 'border-red-500' : ''}`}
                      placeholder="Enter full name"
                    />
                    {errors.name && <p className="text-sm text-red-600">{errors.name}</p>}
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium">Email Address *</label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className={`w-full px-4 py-2.5 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 transition-colors ${errors.email ? 'border-red-500' : ''}`}
                      placeholder="email@example.com"
                    />
                    {errors.email && <p className="text-sm text-red-600">{errors.email}</p>}
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium">Role / Title *</label>
                    <input
                      type="text"
                      value={formData.role}
                      onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                      className={`w-full px-4 py-2.5 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 transition-colors ${errors.role ? 'border-red-500' : ''}`}
                      placeholder="e.g., Senior Engineer"
                    />
                    {errors.role && <p className="text-sm text-red-600">{errors.role}</p>}
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium">Department *</label>
                    <select
                      value={formData.department}
                      onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                      className={`w-full px-4 py-2.5 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 transition-colors ${errors.department ? 'border-red-500' : ''}`}
                    >
                      <option value="">Select department</option>
                      {departments.map((dept) => (
                        <option key={dept} value={dept}>{dept}</option>
                      ))}
                    </select>
                    {errors.department && <p className="text-sm text-red-600">{errors.department}</p>}
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium">Annual Salary *</label>
                    <div className="relative">
                      <span className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                      <input
                        type="text"
                        value={formData.salary}
                        onChange={(e) => handleSalaryChange(e.target.value)}
                        className={`w-full pl-8 pr-4 py-2.5 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 transition-colors ${errors.salary ? 'border-red-500' : ''}`}
                        placeholder="0"
                      />
                    </div>
                    {errors.salary && <p className="text-sm text-red-600">{errors.salary}</p>}
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium">Employment Status</label>
                    <select
                      value={formData.status}
                      onChange={(e) => setFormData({ ...formData, status: e.target.value as 'active' | 'inactive' })}
                      className="w-full px-4 py-2.5 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 transition-colors"
                    >
                      <option value="active">Active</option>
                      <option value="inactive">Inactive</option>
                    </select>
                  </div>
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t border-border">
                  <button
                    type="button"
                    onClick={() => setShowAddDialog(false)}
                    className="px-6 py-2.5 border border-border rounded-lg font-medium hover:bg-muted transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-6 py-2.5 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isSubmitting ? 'Adding...' : 'Add Employee'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard')
  const [employees, setEmployees] = useState<Employee[]>([])
  const [totalPayroll, setTotalPayroll] = useState(0)
  const [activeEmployeesCount, setActiveEmployeesCount] = useState(0)
  const [dbInitialized, setDbInitialized] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const resetDatabase = () => {
    if (confirm('This will delete all employee data and reset the database. Continue?')) {
      clearDatabase()
      window.location.reload()
    }
  }

  useEffect(() => {
    const init = async () => {
      try {
        console.log('Starting database initialization...')
        await initDatabase()
        console.log('Database initialized, setting state...')
        setDbInitialized(true)
        setError(null)
        refreshData()
      } catch (error) {
        console.error('Failed to initialize database:', error)
        setError('Failed to initialize database. Try clearing your browser data or click the reset button below.')
      }
    }
    init()
  }, [])

  const refreshData = () => {
    const emps = getEmployees()
    setEmployees(emps)
    setTotalPayroll(getTotalPayroll())
    setActiveEmployeesCount(getActiveEmployeesCount())
  }

  const handleAddEmployee = async (employee: Omit<Employee, 'id'>) => {
    await dbAddEmployee(employee)
    refreshData()
  }

  const navigation = [
    { id: 'dashboard' as Page, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'payroll' as Page, label: 'Payroll Runs', icon: Calendar },
    { id: 'employees' as Page, label: 'Employees', icon: Users }
  ]

  if (error) {
    return (
      <div className="min-h-screen bg-muted/30 flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <div className="text-red-600 mb-4">
            <AlertCircle className="h-16 w-16 mx-auto" />
          </div>
          <h2 className="text-2xl font-bold mb-2">Database Error</h2>
          <p className="text-muted-foreground mb-6">{error}</p>
          <div className="space-y-3">
            <button
              onClick={resetDatabase}
              className="w-full px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors"
            >
              Reset Database
            </button>
            <p className="text-sm text-muted-foreground">
              This will clear all stored data and start fresh
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (!dbInitialized) {
    return (
      <div className="min-h-screen bg-muted/30 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading database...</p>
          <p className="text-sm text-muted-foreground mt-2">Check browser console for details</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-muted/30">
      <nav className="bg-card border-b border-border px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 bg-primary rounded-lg flex items-center justify-center">
              <DollarSign className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold">PayrollFlow</span>
          </div>
          <div className="flex items-center gap-6">
            {navigation.map((item) => (
              <button
                key={item.id}
                onClick={() => setCurrentPage(item.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${currentPage === item.id ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'}`}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={resetDatabase}
              className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
              title="Reset Database"
            >
              <AlertCircle className="h-5 w-5" />
              <span className="text-sm font-medium hidden md:inline">Reset</span>
            </button>
            <button className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors">
              <Settings className="h-5 w-5" />
              <span className="text-sm font-medium hidden md:inline">Settings</span>
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {currentPage === 'dashboard' && <Dashboard totalPayroll={totalPayroll} activeEmployeesCount={activeEmployeesCount} />}
        {currentPage === 'payroll' && <PayrollRuns />}
        {currentPage === 'employees' && <Employees employees={employees} onAddEmployee={handleAddEmployee} />}
      </main>
    </div>
  )
}

export default App
