const ACTION_COLORS: Record<string, 'success' | 'neutral' | 'primary' | 'warning' | 'error' | 'info'> = {
  Login: 'success',
  Logout: 'neutral',
  Create: 'primary',
  Update: 'warning',
  Delete: 'error',
  Export: 'info'
}

export function getActionColor(action: string) {
  return ACTION_COLORS[action] ?? 'neutral'
}

/** Minimal CSV export for UI tables */
export function exportToCSV(rows: Record<string, unknown>[], filename = 'export') {
  if (!rows.length) return
  const keys = Object.keys(rows[0]!)
  const escape = (v: unknown) => {
    const s = String(v ?? '')
    if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`
    return s
  }
  const header = keys.join(',')
  const lines = rows.map((row) => keys.map((k) => escape(row[k])).join(','))
  const csv = [header, ...lines].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${filename}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
