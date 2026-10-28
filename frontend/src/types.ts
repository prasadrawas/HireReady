export interface JobListing {
  id: string
  ats_source: string
  company: string
  company_slug?: string
  title: string
  location?: string
  remote: boolean
  department?: string
  posted_date?: string
  application_url: string
  description_text?: string
  description_html?: string
  score?: number
  role_fit?: string
  key_gaps?: string[]
  recommendation?: string
  salary?: string
  salary_range?: { min?: number; max?: number; currency?: string }
  red_flags?: string[]
  red_flag_count?: number
  has_tailored_resume?: boolean
  tracker_status?: string
}

export interface RoleSuggestion {
  title: string
  reason: string
}

export interface ScanResponse {
  jobs: JobListing[]
  total: number
  suggestions?: {
    family_suggestions?: RoleSuggestion[]
    scan_suggestions?: { title: string; seen_count: number }[]
  }
}

export interface TrackerApplication {
  job_id: string
  company: string
  title: string
  application_url: string
  output_dir?: string
  coverage_score?: number
  validation_passed?: boolean
  needs_review_count?: number
  status: string
  created_at?: string
  updated_at?: string
  notes?: string
}

export interface JobOutput {
  exists: boolean
  job_id?: string
  has_pdf?: boolean
  has_html?: boolean
  has_cover_letter?: boolean
  cover_letter?: string
  job_analysis?: any
  match_report?: any
  validation_report?: any
  change_summary?: string
}

export interface AppStats {
  total_jobs_scanned: number
  total_applications: number
  pipeline: Record<string, number>
  ats_configured_count: number
}
