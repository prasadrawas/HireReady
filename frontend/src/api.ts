import { AppStats, JobOutput, MasterResumeData, ScanResponse, TrackerApplication } from './types'

const API_BASE = '/api'

export async function fetchStats(): Promise<AppStats> {
  const res = await fetch(`${API_BASE}/stats`)
  if (!res.ok) throw new Error('Failed to fetch stats')
  return res.json()
}

export async function fetchJobs(search = '', minScore = 0): Promise<ScanResponse> {
  const params = new URLSearchParams()
  if (search) params.set('search', search)
  if (minScore > 0) params.set('min_score', minScore.toString())
  const res = await fetch(`${API_BASE}/jobs?${params}`)
  if (!res.ok) throw new Error('Failed to fetch jobs')
  return res.json()
}

export async function tailorJob(jobId: string, coverLetter = true): Promise<{ success: boolean; data: JobOutput }> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/tailor`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cover_letter: coverLetter }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to tailor resume' }))
    throw new Error(err.detail || 'Failed to tailor resume')
  }
  return res.json()
}

export async function fetchJobOutput(jobId: string): Promise<JobOutput> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/output`)
  if (!res.ok) throw new Error('Failed to fetch job output')
  return res.json()
}

export async function fetchTracker(): Promise<{ applications: TrackerApplication[] }> {
  const res = await fetch(`${API_BASE}/tracker`)
  if (!res.ok) throw new Error('Failed to fetch tracker')
  return res.json()
}

export async function updateTrackerStatus(jobId: string, status: string, notes?: string) {
  const res = await fetch(`${API_BASE}/tracker/${jobId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status, notes }),
  })
  if (!res.ok) throw new Error('Failed to update tracker')
  return res.json()
}

export async function deleteTrackerJob(jobId: string) {
  const res = await fetch(`${API_BASE}/tracker/${jobId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to delete tracker job')
  return res.json()
}

export async function fetchPreferences(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/preferences`)
  if (!res.ok) throw new Error('Failed to fetch preferences')
  return res.json()
}

export async function savePreferences(data: Record<string, any>) {
  const res = await fetch(`${API_BASE}/preferences`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to save preferences')
  return res.json()
}

export async function fetchAtsLinks(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/ats-links`)
  if (!res.ok) throw new Error('Failed to fetch ATS links')
  return res.json()
}

export async function addAtsLink(payload: { url?: string; platform?: string; company_slug?: string }) {
  const res = await fetch(`${API_BASE}/ats-links`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to add ATS link' }))
    throw new Error(err.detail || 'Failed to add ATS link')
  }
  return res.json()
}

export async function deleteAtsLink(platform: string, company_slug: string) {
  const res = await fetch(`${API_BASE}/ats-links/${platform}/${company_slug}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error('Failed to delete ATS link')
  return res.json()
}

export async function tailorBulk(jobIds: string[], coverLetter = false): Promise<{ results: Record<string, any> }> {
  const results: Record<string, any> = {}
  for (const id of jobIds) {
    try {
      const res = await tailorJob(id, coverLetter)
      results[id] = { success: true, data: res.data }
    } catch (err: any) {
      results[id] = { success: false, error: err.message }
    }
  }
  return { results }
}

export function exportApplicationsCSV(applications: TrackerApplication[]): void {
  const headers = ['Company', 'Title', 'Status', 'Coverage', 'Salary', 'Applied URL', 'Submitted', 'Updated']
  const rows = applications.map((a) => [
    a.company,
    a.title,
    a.status,
    a.coverage_score ? `${Math.round(a.coverage_score * 100)}%` : '',
    a.salary || '',
    a.application_url,
    a.submitted_at || '',
    a.updated_at || '',
  ])
  const csv = [headers, ...rows]
    .map((r) =>
      r
        .map((c) => `"${(c || '').replace(/"/g, '""')}"`)
        .join(',')
    )
    .join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `hireready_applications_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export async function fetchMasterResumeData(): Promise<{ success: boolean; resume: MasterResumeData; raw_html_exists: boolean }> {
  const res = await fetch(`${API_BASE}/resume/master/data`)
  if (!res.ok) throw new Error('Failed to load master resume data')
  return res.json()
}
