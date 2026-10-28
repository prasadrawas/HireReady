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
  red_flag_verdict?: string
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
  salary?: string
  linkedin_url?: string
  submitted_at?: string
  followup_dates?: { date: string; days_after: number; completed: boolean }[]
  interview_stages?: { stage: string; date: string; notes: string }[]
  notes?: { text: string; added_at: string }[] | string
}

export interface RedFlagDetail {
  category: string
  signal: string
  evidence: string
  severity: string
}

export interface RedFlagsReport {
  total: number
  critical: number
  warnings: number
  verdict: string
  flags: RedFlagDetail[]
}

export interface CompanyBrief {
  company_name: string
  industry: string
  stage: string
  estimated_size: string
  known_for: string
  tech_stack_signals: string[]
  culture_signals: string[]
  funding_status: string
  glassdoor_sentiment: string
  notable_facts: string[]
  potential_concerns: string[]
  verdict: string
}

export interface SalaryInfo {
  min_salary?: number
  max_salary?: number
  currency: string
  display: string
}

export interface JobOutput {
  exists: boolean
  job_id?: string
  has_pdf?: boolean
  has_html?: boolean
  has_cover_letter?: boolean
  cover_letter?: string
  cover_letter_txt?: string
  cover_letter_html?: string
  job_analysis?: any
  match_report?: any
  validation_report?: any
  change_summary?: string
  red_flags?: RedFlagsReport
  company_brief?: CompanyBrief
  salary_info?: SalaryInfo
  application_urls?: string
}

export interface AppStats {
  total_jobs_scanned: number
  total_applications: number
  pipeline: Record<string, number>
  ats_configured_count: number
}
