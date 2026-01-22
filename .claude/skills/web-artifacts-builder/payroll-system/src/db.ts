import initSqlJs, { Database, SqlJsStatic } from 'sql.js'

let SQL: SqlJsStatic | null = null
let db: Database | null = null
const DB_VERSION = '2.0'

export const clearDatabase = () => {
  console.log('Clearing database from localStorage...')
  localStorage.removeItem('payrollDB')
  localStorage.removeItem('payrollDB_version')
}

export const initDatabase = async () => {
  if (SQL) return db

  try {
    console.log('Initializing SQLite database...')
    SQL = await initSqlJs({
      locateFile: () =>
        'https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.13.0/sql-wasm.wasm',
    })

    const savedDB = localStorage.getItem('payrollDB')
    const savedVersion = localStorage.getItem('payrollDB_version')
    let dbData: Uint8Array | undefined
    let hasValidSavedData = false

    if (savedDB && savedVersion === DB_VERSION) {
      try {
        console.log('Loading database from localStorage...')
        const binaryString = atob(savedDB)
        const bytes = new Uint8Array(binaryString.length)
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i)
        }
        dbData = bytes
        hasValidSavedData = true
        console.log('Successfully loaded database from localStorage')
      } catch (e) {
        console.error('Failed to load saved database:', e)
        clearDatabase()
        hasValidSavedData = false
      }
    } else {
      if (savedVersion && savedVersion !== DB_VERSION) {
        console.log('Database version mismatch, clearing old data')
        clearDatabase()
      }
      console.log('No saved database found or version mismatch, will create new one')
    }

    db = new SQL.Database(dbData)

    db.run(`
      CREATE TABLE IF NOT EXISTS employees (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        role TEXT NOT NULL,
        department TEXT NOT NULL,
        salary REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'active'
      )
    `)

    if (!hasValidSavedData) {
      console.log('Seeding database with initial data...')
      seedDatabase(db)
      console.log('Database seeded successfully')
    } else {
      console.log('Using existing database')
    }

    localStorage.setItem('payrollDB_version', DB_VERSION)
    console.log('Database initialized successfully')
    return db
  } catch (e) {
    console.error('Failed to initialize database:', e)
    clearDatabase()
    throw e
  }
}

const seedDatabase = (database: Database) => {
  try {
    const initialData = [
      { id: '1', name: 'Sarah Chen', email: 'sarah.chen@company.com', role: 'Senior Engineer', department: 'Engineering', salary: 135000, status: 'active' },
      { id: '2', name: 'Michael Rodriguez', email: 'michael.r@company.com', role: 'Product Designer', department: 'Design', salary: 118000, status: 'active' },
      { id: '3', name: 'Emily Watson', email: 'emily.w@company.com', role: 'Engineering Manager', department: 'Engineering', salary: 165000, status: 'active' },
      { id: '4', name: 'James Kim', email: 'james.kim@company.com', role: 'Data Analyst', department: 'Analytics', salary: 92000, status: 'active' },
      { id: '5', name: 'Anna Martinez', email: 'anna.m@company.com', role: 'HR Specialist', department: 'Human Resources', salary: 78000, status: 'active' },
      { id: '6', name: 'David Park', email: 'david.p@company.com', role: 'Senior Developer', department: 'Engineering', salary: 125000, status: 'active' }
    ]

    console.log('Inserting initial data:', initialData.length, 'records')
    const stmt = database.prepare('INSERT INTO employees (id, name, email, role, department, salary, status) VALUES (?, ?, ?, ?, ?, ?, ?)')
    initialData.forEach((emp, index) => {
      console.log(`Inserting employee ${index + 1}:`, emp.name)
      stmt.run(emp.id, emp.name, emp.email, emp.role, emp.department, emp.salary, emp.status)
    })
    stmt.free()
    console.log('Successfully inserted all initial data')
  } catch (error) {
    console.error('Failed to seed database:', error)
    throw error
  }
}

export const saveDatabase = () => {
  if (!db) return

  try {
    const data = db.export()
    const binaryString = String.fromCharCode.apply(null, Array.from(data))
    localStorage.setItem('payrollDB', btoa(binaryString))
    localStorage.setItem('payrollDB_version', DB_VERSION)
    console.log('Database saved successfully')
  } catch (e) {
    console.error('Failed to save database:', e)
  }
}

export const getEmployees = () => {
  if (!db) return []

  const results = db.exec('SELECT * FROM employees ORDER BY name')
  if (results.length === 0) return []

  const columns = results[0].columns
  return results[0].values.map(row => {
    const obj: any = {}
    columns.forEach((col, i) => {
      obj[col] = row[i]
    })
    return obj as {
      id: string
      name: string
      email: string
      role: string
      department: string
      salary: number
      status: 'active' | 'inactive'
    }
  })
}

export const addEmployee = (employee: {
  name: string
  email: string
  role: string
  department: string
  salary: number
  status: 'active' | 'inactive'
}) => {
  if (!db) throw new Error('Database not initialized')

  const id = Date.now().toString()
  db.run(
    'INSERT INTO employees (id, name, email, role, department, salary, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
    [id, employee.name, employee.email, employee.role, employee.department, employee.salary, employee.status]
  )
  saveDatabase()
  return id
}

export const updateEmployee = (id: string, employee: Partial<{
  name: string
  email: string
  role: string
  department: string
  salary: number
  status: 'active' | 'inactive'
}>) => {
  if (!db) throw new Error('Database not initialized')

  const fields: string[] = []
  const values: any[] = []

  if (employee.name !== undefined) {
    fields.push('name = ?')
    values.push(employee.name)
  }
  if (employee.email !== undefined) {
    fields.push('email = ?')
    values.push(employee.email)
  }
  if (employee.role !== undefined) {
    fields.push('role = ?')
    values.push(employee.role)
  }
  if (employee.department !== undefined) {
    fields.push('department = ?')
    values.push(employee.department)
  }
  if (employee.salary !== undefined) {
    fields.push('salary = ?')
    values.push(employee.salary)
  }
  if (employee.status !== undefined) {
    fields.push('status = ?')
    values.push(employee.status)
  }

  if (fields.length === 0) return

  values.push(id)
  db.run(`UPDATE employees SET ${fields.join(', ')} WHERE id = ?`, values)
  saveDatabase()
}

export const deleteEmployee = (id: string) => {
  if (!db) throw new Error('Database not initialized')

  db.run('DELETE FROM employees WHERE id = ?', [id])
  saveDatabase()
}

export const getTotalPayroll = () => {
  if (!db) return 0

  const result = db.exec('SELECT SUM(salary) as total FROM employees WHERE status = "active"')
  if (result.length === 0) return 0

  return result[0].values[0][0] as number || 0
}

export const getActiveEmployeesCount = () => {
  if (!db) return 0

  const result = db.exec('SELECT COUNT(*) as count FROM employees WHERE status = "active"')
  if (result.length === 0) return 0

  return result[0].values[0][0] as number || 0
}
