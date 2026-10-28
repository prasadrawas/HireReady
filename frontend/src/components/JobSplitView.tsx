import React, { useState, useMemo, useEffect } from 'react'
import {
  ExternalLink,
  Sparkles,
  MapPin,
  DollarSign,
  AlertTriangle,
  CheckCircle2,
  Bookmark,
  Building2,
  Calendar,
  Search,
  Filter,
  FileText,
  Download,
  Copy,
  Check,
  ChevronRight,
  ShieldCheck,
  Briefcase,
  Share2,
  MoreHorizontal,
  Clock,
  Compass,
  Flag,
  Info,
  GitCompare,
  Square,
  CheckSquare,
  Link,
  Bot,
} from 'lucide-react'
import { JobListing, JobOutput } from '../types'
import { CompanyLogo } from './CompanyLogo'

interface JobSplitViewProps {
  jobs: JobListing[]
  selectedJob: JobListing | null
  onSelectJob: (job: JobListing) => void
  onTailor: (job: JobListing, coverLetter: boolean) => Promise<void>
  onTrack: (job: JobListing, status: string) => void
  tailoredOutput: JobOutput | null
  isTailoring: boolean
  activeJobIdTailoring: string | null
  bulkTailorIds: Set<string>
  onToggleBulkId: (jobId: string) => void
  onBulkTailor: (coverLetter?: boolean) => void
  onAutoApply?: (job: JobListing, autoSubmit?: boolean) => Promise<void>
  isAutoApplying?: boolean
  activeJobIdAutoApplying?: string | null
  darkMode: boolean
}

type DetailTab = 'jd' | 'red_flags' | 'company' | 'resume' | 'diff' | 'cover_letter' | 'validation'

function getDaysAgo(dateStr?: string): string | null {
  if (!dateStr) return null
  try {
    const posted = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - posted.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return '1 day ago'
    if (diffDays < 7) return `${diffDays} days ago`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`
    return `${Math.floor(diffDays / 30)}mo ago`
  } catch {
    return null
  }
}

function parseDiffFromChangeSummary(changeSummary: string): { removed: string[]; added: string[]; keywords: string[] } {
  const removed: string[] = []
  const added: string[] = []
  const keywords: string[] = []

  const lines = changeSummary.split('\n')
  for (const line of lines) {
    const trimmed = line.trim()
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const content = trimmed.slice(2).trim()
      if (content.toLowerCase().includes('removed') || content.toLowerCase().includes('replaced') || content.toLowerCase().includes('original')) {
        removed.push(content)
      } else if (content.toLowerCase().includes('added') || content.toLowerCase().includes('new') || content.toLowerCase().includes('tailored') || content.toLowerCase().includes('updated')) {
        added.push(content)
      } else {
        added.push(content)
      }
    }

    // Extract keywords wrapped in backticks or bold
    const keywordMatches = trimmed.match(/`([^`]+)`/g) || []
    for (const kw of keywordMatches) {
      keywords.push(kw.replace(/`/g, ''))
    }
    const boldMatches = trimmed.match(/\*\*([^*]+)\*\*/g) || []
    for (const bm of boldMatches) {
      keywords.push(bm.replace(/\*\*/g, ''))
    }
  }

  return { removed, added, keywords: [...new Set(keywords)] }
}

function getSeverityColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case 'critical':
    case 'high':
      return 'bg-red-50 border-red-200 text-red-800'
    case 'medium':
    case 'warning':
      return 'bg-amber-50 border-amber-200 text-amber-800'
    case 'low':
    case 'info':
      return 'bg-blue-50 border-blue-200 text-blue-700'
    default:
      return 'bg-slate-50 border-slate-200 text-slate-700'
  }
}

function getVerdictColor(verdict: string): string {
  switch (verdict) {
    case 'clean':
      return 'text-emerald-700 bg-emerald-50 border-emerald-200'
    case 'mostly_clean':
      return 'text-green-700 bg-green-50 border-green-200'
    case 'minor_concerns':
      return 'text-amber-700 bg-amber-50 border-amber-200'
    case 'proceed_with_caution':
      return 'text-orange-700 bg-orange-50 border-orange-200'
    case 'avoid':
      return 'text-red-700 bg-red-50 border-red-200'
    default:
      return 'text-slate-700 bg-slate-50 border-slate-200'
  }
}

export const JobSplitView: React.FC<JobSplitViewProps> = ({
  jobs,
  selectedJob,
  onSelectJob,
  onTailor,
  onTrack,
  tailoredOutput,
  isTailoring,
  activeJobIdTailoring,
  bulkTailorIds,
  onToggleBulkId,
  onBulkTailor,
  onAutoApply,
  isAutoApplying,
  activeJobIdAutoApplying,
  darkMode,
}) => {
  // Filter states
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedPlatform, setSelectedPlatform] = useState<string>('all')
  const [selectedCompany, setSelectedCompany] = useState<string>('all')
  const [remoteOnly, setRemoteOnly] = useState(false)
  const [minScoreFilter, setMinScoreFilter] = useState<number>(0)
  const [tailoredOnly, setTailoredOnly] = useState(false)
  const [minSalaryFilter, setMinSalaryFilter] = useState<number>(0)
  const [postedWithin, setPostedWithin] = useState<number>(0) // 0 = any, days threshold
  const [activeTab, setActiveTab] = useState<DetailTab>('jd')
  const [copiedCoverLetter, setCopiedCoverLetter] = useState(false)
  const [copiedUrl, setCopiedUrl] = useState(false)

  // Unique ATS platforms
  const platforms = useMemo(() => {
    const set = new Set<string>()
    jobs.forEach((j) => {
      if (j.ats_source) set.add(j.ats_source)
    })
    return Array.from(set)
  }, [jobs])

  // Unique companies (sorted alphabetically)
  const companies = useMemo(() => {
    const set = new Set<string>()
    jobs.forEach((j) => {
      if (j.company) set.add(j.company)
    })
    return Array.from(set).sort()
  }, [jobs])

  // Filtered jobs
  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
      if (searchQuery) {
        const q = searchQuery.toLowerCase()
        const matchesTitle = job.title.toLowerCase().includes(q)
        const matchesCompany = job.company.toLowerCase().includes(q)
        const matchesLocation = (job.location || '').toLowerCase().includes(q)
        if (!matchesTitle && !matchesCompany && !matchesLocation) return false
      }
      if (selectedPlatform !== 'all' && job.ats_source !== selectedPlatform) return false
      if (selectedCompany !== 'all' && job.company !== selectedCompany) return false
      if (remoteOnly && !job.remote) return false
      if (minScoreFilter > 0 && (job.score || 0) < minScoreFilter) return false
      if (tailoredOnly && !job.has_tailored_resume) return false
      if (minSalaryFilter > 0 && job.salary_range) {
        const minSal = job.salary_range.min || 0
        if (minSal < minSalaryFilter * 1000) return false
      }
      if (postedWithin > 0 && job.posted_date) {
        const posted = new Date(job.posted_date)
        const now = new Date()
        const diffDays = Math.floor((now.getTime() - posted.getTime()) / (1000 * 60 * 60 * 24))
        if (diffDays > postedWithin) return false
      }
      return true
    })
  }, [jobs, searchQuery, selectedPlatform, selectedCompany, remoteOnly, minScoreFilter, tailoredOnly, minSalaryFilter, postedWithin])

  // Pagination state
  const [currentPage, setCurrentPage] = useState<number>(1)
  const [pageSize, setPageSize] = useState<number>(15)

  useEffect(() => {
    setCurrentPage(1)
  }, [searchQuery, selectedPlatform, selectedCompany, remoteOnly, minScoreFilter, tailoredOnly, minSalaryFilter, postedWithin])

  const totalPages = Math.max(1, Math.ceil(filteredJobs.length / (pageSize || 1)))
  const paginatedJobs = useMemo(() => {
    if (pageSize <= 0) return filteredJobs
    const start = (currentPage - 1) * pageSize
    return filteredJobs.slice(start, start + pageSize)
  }, [filteredJobs, currentPage, pageSize])

  // Auto-select first job if none selected
  const activeJob = selectedJob || filteredJobs[0] || null

  const handleCopyCoverLetter = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedCoverLetter(true)
    setTimeout(() => setCopiedCoverLetter(false), 2000)
  }

  const handleCopyUrl = (url: string) => {
    navigator.clipboard.writeText(url)
    setCopiedUrl(true)
    setTimeout(() => setCopiedUrl(false), 2000)
  }

  const parseAndFormatJD = (rawHtml?: string, rawText?: string): string => {
    if (!rawHtml && !rawText) return '<p class="text-slate-500">No description provided.</p>'

    let str = rawHtml || rawText || ''

    // Decode HTML entities repeatedly until real HTML tags appear.
    // Greenhouse and some ATS APIs return escaped HTML: &lt;p&gt; instead of <p>
    // DOMParser.textContent decodes entities: "&lt;p&gt;" → "<p>"
    let maxPasses = 5
    while (maxPasses-- > 0 && (str.includes('&lt;') || str.includes('&amp;') || str.includes('&#'))) {
      const textarea = document.createElement('textarea')
      textarea.innerHTML = str
      const decoded = textarea.value
      if (decoded === str) break
      str = decoded
    }

    // If the string has no HTML tags at all, it's plain text — wrap in paragraphs
    if (!/<[a-z][\s\S]*>/i.test(str)) {
      str = str
        .split(/\n\n+/)
        .map((p) => `<p>${p.replace(/\n/g, '<br/>')}</p>`)
        .join('')
    }

    // Strip inline styles from external ATS boards (font-family, colors, backgrounds)
    str = str.replace(/\s*style\s*=\s*"[^"]*"/gi, '')
    str = str.replace(/\s*style\s*=\s*'[^']*'/gi, '')

    return str
  }

  // Company avatar fallback color generator
  const getAvatarColor = (name: string) => {
    const colors = [
      'bg-[#0a66c2]',
      'bg-[#057642]',
      'bg-[#7c3aed]',
      'bg-[#b45309]',
      'bg-[#be185d]',
      'bg-[#0f766e]',
      'bg-[#4338ca]',
    ]
    let hash = 0
    for (let i = 0; i < name.length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash)
    }
    return colors[Math.abs(hash) % colors.length]
  }

  const coverLetterText = tailoredOutput?.cover_letter_txt || tailoredOutput?.cover_letter

  // Skeleton component for loading state
  const SkeletonPanel = () => (
    <div className="p-6 space-y-6 animate-pulse">
      <div className="flex items-center gap-3.5">
        <div className="skeleton w-14 h-14 rounded-lg" />
        <div className="flex-1 space-y-2">
          <div className="skeleton h-4 w-32" />
          <div className="skeleton h-6 w-64" />
        </div>
      </div>
      <div className="flex gap-2">
        <div className="skeleton h-8 w-24 rounded-full" />
        <div className="skeleton h-8 w-20 rounded-full" />
        <div className="skeleton h-8 w-28 rounded-full" />
      </div>
      <div className="skeleton h-32 w-full rounded-xl" />
      <div className="space-y-2">
        <div className="skeleton h-4 w-full" />
        <div className="skeleton h-4 w-3/4" />
        <div className="skeleton h-4 w-5/6" />
        <div className="skeleton h-4 w-2/3" />
      </div>
    </div>
  )

  return (
    <div className={`flex flex-col h-[calc(100vh-3.5rem)] overflow-hidden ${darkMode ? 'bg-[#1a1a2e]' : 'bg-[#f4f2ee]'}`}>
      {/* TOP FILTER BAR */}
      <div className={`border-b shrink-0 shadow-xs ${darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'}`}>
        <div className="max-w-7xl w-full mx-auto px-4 sm:px-5 py-2.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 flex-1">
          {/* Search Input */}
          <div className="relative min-w-[220px] max-w-xs">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by title, skill, or company"
              className={`w-full border border-transparent rounded-full pl-9 pr-4 py-1.5 text-xs placeholder-slate-500 focus:outline-none transition-all ${
                darkMode
                  ? 'bg-[#1e3a5f] hover:bg-[#243f63] focus:bg-[#1a1a2e] focus:border-[#0a66c2] text-slate-200'
                  : 'bg-[#edf3f8] hover:bg-[#e4ebf2] focus:bg-white focus:border-[#0a66c2] text-slate-900'
              }`}
            />
          </div>

          {/* --- Filters in logical order --- */}

          {/* 1. Posted Within */}
          <select
            value={postedWithin}
            onChange={(e) => setPostedWithin(parseInt(e.target.value))}
            className={`rounded-full px-3.5 py-1.5 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-[#0a66c2] cursor-pointer border ${
              darkMode
                ? 'bg-[#16213e] hover:bg-[#1e3a5f] text-slate-300 border-[#1e3a5f]'
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            <option value={0}>Date: Any time</option>
            <option value={1}>Today</option>
            <option value={3}>Last 3 days</option>
            <option value={7}>This week</option>
            <option value={14}>Last 2 weeks</option>
            <option value={30}>This month</option>
          </select>

          {/* 2. Company */}
          <select
            value={selectedCompany}
            onChange={(e) => setSelectedCompany(e.target.value)}
            className={`rounded-full px-3.5 py-1.5 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-[#0a66c2] cursor-pointer border ${
              darkMode
                ? 'bg-[#16213e] hover:bg-[#1e3a5f] text-slate-300 border-[#1e3a5f]'
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            <option value="all">Company: All ({companies.length})</option>
            {companies.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>

          {/* 3. Match Score */}
          <select
            value={minScoreFilter}
            onChange={(e) => setMinScoreFilter(parseFloat(e.target.value))}
            className={`rounded-full px-3.5 py-1.5 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-[#0a66c2] cursor-pointer border ${
              darkMode
                ? 'bg-[#16213e] hover:bg-[#1e3a5f] text-slate-300 border-[#1e3a5f]'
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            <option value={0}>Match: All</option>
            <option value={0.7}>70%+ Strong</option>
            <option value={0.5}>50%+ Medium</option>
            <option value={0.4}>40%+ Good</option>
          </select>

          {/* 4. Salary */}
          <select
            value={minSalaryFilter}
            onChange={(e) => setMinSalaryFilter(parseInt(e.target.value))}
            className={`rounded-full px-3.5 py-1.5 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-[#0a66c2] cursor-pointer border ${
              darkMode
                ? 'bg-[#16213e] hover:bg-[#1e3a5f] text-slate-300 border-[#1e3a5f]'
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            <option value={0}>Salary: Any</option>
            <option value={80}>$80k+</option>
            <option value={100}>$100k+</option>
            <option value={120}>$120k+</option>
            <option value={150}>$150k+</option>
            <option value={200}>$200k+</option>
          </select>

          {/* 5. ATS Platform */}
          <select
            value={selectedPlatform}
            onChange={(e) => setSelectedPlatform(e.target.value)}
            className={`rounded-full px-3.5 py-1.5 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-[#0a66c2] cursor-pointer border ${
              darkMode
                ? 'bg-[#16213e] hover:bg-[#1e3a5f] text-slate-300 border-[#1e3a5f]'
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            <option value="all">ATS: All</option>
            {platforms.map((p) => (
              <option key={p} value={p}>
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </option>
            ))}
          </select>

          {/* 6. Remote */}
          <button
            onClick={() => setRemoteOnly(!remoteOnly)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer ${
              remoteOnly
                ? 'bg-[#01754f] text-white border-transparent'
                : darkMode
                ? 'bg-[#16213e] hover:bg-[#1e3a5f] text-slate-300 border-[#1e3a5f]'
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            Remote {remoteOnly && '✓'}
          </button>

          {/* 7. Tailored Only */}
          <button
            onClick={() => setTailoredOnly(!tailoredOnly)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer ${
              tailoredOnly
                ? 'bg-[#01754f] text-white border-transparent'
                : darkMode
                ? 'bg-[#16213e] hover:bg-[#1e3a5f] text-slate-300 border-[#1e3a5f]'
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            Tailored {tailoredOnly && '✓'}
          </button>

          {(searchQuery || remoteOnly || tailoredOnly || selectedPlatform !== 'all' || selectedCompany !== 'all' || minScoreFilter > 0 || minSalaryFilter > 0 || postedWithin > 0) && (
            <button
              onClick={() => {
                setSearchQuery('')
                setRemoteOnly(false)
                setTailoredOnly(false)
                setSelectedPlatform('all')
                setSelectedCompany('all')
                setMinScoreFilter(0)
                setMinSalaryFilter(0)
                setPostedWithin(0)
              }}
              className="text-xs text-[#0a66c2] hover:text-[#004182] font-semibold px-2 py-1 cursor-pointer"
            >
              Reset filters
            </button>
          )}
        </div>

        {/* Bulk Tailor & Results Count */}
        <div className="flex items-center gap-3 shrink-0">
          {bulkTailorIds.size > 0 && (
            <button
              onClick={() => onBulkTailor(false)}
              className="px-3.5 py-1.5 rounded-full bg-purple-700 hover:bg-purple-800 text-white text-xs font-bold flex items-center gap-1.5 shadow-xs cursor-pointer transition-all"
            >
              <Sparkles className="w-3.5 h-3.5" />
              Tailor Selected ({bulkTailorIds.size})
            </button>
          )}
          <div className={`text-xs font-medium flex items-center gap-1.5 ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
            <span>{filteredJobs.length} results</span>
          </div>
        </div>
        </div>
      </div>

      {/* MAIN SPLIT VIEW */}
      <div className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-5 flex gap-5 overflow-hidden">
        {/* LEFT COLUMN: Job Listings with Pagination */}
        <div className={`w-full md:w-[380px] lg:w-[410px] xl:w-[430px] rounded-xl border shrink-0 flex flex-col shadow-xs overflow-hidden ${
          darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'
        }`}>
          {/* Scrollable Job Listings */}
          <div className={`flex-1 overflow-y-auto divide-y ${
            darkMode ? 'divide-[#1e3a5f]' : 'divide-slate-100'
          }`}>
            {filteredJobs.length === 0 ? (
              <div className="p-10 text-center">
                <Briefcase className={`w-10 h-10 mx-auto mb-2 ${darkMode ? 'text-slate-600' : 'text-slate-300'}`} />
                <p className={`font-semibold ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>No matching jobs</p>
                <p className={`text-xs mt-1 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>Try resetting or broadening your filters.</p>
                <button
                  onClick={() => {
                    setSearchQuery('')
                    setRemoteOnly(false)
                    setTailoredOnly(false)
                    setSelectedPlatform('all')
                    setMinScoreFilter(0)
                    setMinSalaryFilter(0)
                  }}
                  className="mt-3 px-4 py-1.5 rounded-full bg-[#0a66c2] text-white text-xs font-semibold cursor-pointer"
                >
                  Reset All Filters
                </button>
              </div>
            ) : (
              paginatedJobs.map((job) => {
                const isSelected = activeJob?.id === job.id
                const matchPct = Math.round((job.score || 0.5) * 100)
                const avatarColor = getAvatarColor(job.company)
                const freshness = getDaysAgo(job.posted_date)
                const isBulkSelected = bulkTailorIds.has(job.id)

                return (
                  <div
                    key={job.id}
                    className={`p-4 transition-all cursor-pointer relative flex gap-3.5 ${
                      darkMode ? 'hover:bg-[#1e3a5f]' : 'hover:bg-slate-50'
                    } ${
                      isSelected
                        ? darkMode
                          ? 'bg-[#1e3a5f]/70 border-l-4 border-l-[#0a66c2]'
                          : 'bg-[#edf3f8]/70 border-l-4 border-l-[#0a66c2]'
                        : 'border-l-4 border-l-transparent'
                    }`}
                  >
                    {/* Bulk Select Checkbox */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        onToggleBulkId(job.id)
                      }}
                      className={`shrink-0 mt-1 cursor-pointer ${isBulkSelected ? 'text-[#0a66c2]' : darkMode ? 'text-slate-500' : 'text-slate-300'}`}
                      title="Select for bulk tailor"
                    >
                      {isBulkSelected ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
                    </button>

                    {/* Company Logo Square */}
                    <div onClick={() => onSelectJob(job)}>
                      <CompanyLogo
                        company={job.company}
                        companySlug={job.company_slug}
                        className="w-12 h-12 rounded-lg text-sm"
                      />
                    </div>

                    {/* Job Summary */}
                    <div className="flex-1 min-w-0" onClick={() => onSelectJob(job)}>
                      <h4
                        className={`text-sm font-semibold truncate ${
                          isSelected ? 'text-[#0a66c2]' : darkMode ? 'text-slate-100 hover:text-[#0a66c2]' : 'text-slate-900 hover:text-[#0a66c2]'
                        }`}
                      >
                        {job.title}
                      </h4>

                      <p className={`text-xs font-normal mt-0.5 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>{job.company}</p>

                      <div className="flex items-center gap-1.5 mt-0.5">
                        <p className={`text-xs truncate ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                          {job.location || 'Remote'}
                        </p>
                        {job.workplace_type && (
                          <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                            job.workplace_type === 'Remote'
                              ? 'bg-emerald-100/70 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                              : job.workplace_type === 'Hybrid'
                              ? 'bg-indigo-100/70 text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300'
                              : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
                          }`}>
                            {job.workplace_type}
                          </span>
                        )}
                      </div>

                      {job.salary && (
                        <p className={`text-xs font-medium mt-1 truncate ${darkMode ? 'text-slate-300' : 'text-slate-600'}`}>
                          {job.salary}
                        </p>
                      )}

                      {/* Tags & Status */}
                      <div className={`flex items-center justify-between w-full mt-2 text-[11px]`}>
                        {job.has_tailored_resume ? (
                          <span className="flex items-center gap-1 text-[#057642] font-semibold shrink-0">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Tailored
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-[#057642] font-medium shrink-0">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Reviewing
                          </span>
                        )}

                        <span
                          className={`font-semibold px-2 py-0.5 rounded-full shrink-0 ${
                            matchPct >= 70
                              ? 'bg-emerald-50 text-emerald-700'
                              : matchPct >= 50
                              ? 'bg-blue-50 text-blue-700'
                              : 'bg-slate-100 text-slate-600'
                          }`}
                        >
                          {matchPct}% Match
                        </span>

                        {freshness && (
                          <span className={`flex items-center gap-0.5 shrink-0 ${darkMode ? 'text-slate-400' : 'text-slate-400'}`}>
                            <Clock className="w-3 h-3" />
                            {freshness}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>

          {/* Sticky Pagination Footer */}
          {filteredJobs.length > 0 && (
            <div className={`p-2.5 px-3 border-t shrink-0 flex items-center justify-between text-xs font-medium ${
              darkMode ? 'bg-[#16213e] border-[#1e3a5f] text-slate-300' : 'bg-slate-50 border-slate-200 text-slate-600'
            }`}>
              <div className="flex items-center gap-1">
                <span>Page</span>
                <span className="font-bold text-[#0a66c2]">{currentPage}</span>
                <span>of</span>
                <span className="font-bold">{totalPages}</span>
                <span className="text-[11px] text-slate-400 ml-1">({filteredJobs.length})</span>
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage <= 1}
                  className="px-2.5 py-1 rounded border disabled:opacity-40 hover:bg-slate-200 dark:hover:bg-slate-700 transition cursor-pointer disabled:cursor-not-allowed text-xs font-semibold"
                >
                  Prev
                </button>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage >= totalPages}
                  className="px-2.5 py-1 rounded border disabled:opacity-40 hover:bg-slate-200 dark:hover:bg-slate-700 transition cursor-pointer disabled:cursor-not-allowed text-xs font-semibold"
                >
                  Next
                </button>

                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value))
                    setCurrentPage(1)
                  }}
                  className={`rounded px-1.5 py-1 border text-xs cursor-pointer ${
                    darkMode ? 'bg-[#1e3a5f] text-slate-300 border-[#2a4a6f]' : 'bg-white text-slate-700 border-slate-300'
                  }`}
                >
                  <option value={10}>10 / page</option>
                  <option value={15}>15 / page</option>
                  <option value={25}>25 / page</option>
                  <option value={50}>50 / page</option>
                  <option value={0}>All</option>
                </select>
              </div>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: Detailed Job View */}
        <div className={`flex-1 rounded-xl border overflow-y-auto shadow-xs flex flex-col ${
          darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'
        }`}>
          {activeJob ? (
            <div className="p-6 space-y-6">
              {/* Header section */}
              <div>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3.5">
                    <CompanyLogo
                      company={activeJob.company}
                      companySlug={activeJob.company_slug}
                      className="w-14 h-14 rounded-lg text-lg"
                    />
                    <div>
                      <span className={`text-sm font-semibold hover:text-[#0a66c2] cursor-pointer ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>
                        {activeJob.company}
                      </span>
                      <h2 className={`text-2xl font-bold tracking-tight mt-0.5 ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>
                        {activeJob.title}
                      </h2>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 text-slate-400">
                    <button className={`p-2 rounded-full transition-colors cursor-pointer ${darkMode ? 'hover:bg-[#1e3a5f] text-slate-400' : 'hover:bg-slate-100 text-slate-600'}`}>
                      <MoreHorizontal className="w-5 h-5" />
                    </button>
                  </div>
                </div>

                {/* Metadata Line */}
                <div className={`flex flex-wrap items-center gap-2 mt-3 text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                  <span className={`font-medium ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>{activeJob.location || 'Remote'}</span>
                  <span>&bull;</span>
                  {activeJob.posted_date && (
                    <>
                      <span>Posted {getDaysAgo(activeJob.posted_date) || activeJob.posted_date}</span>
                      <span>&bull;</span>
                    </>
                  )}
                  <span>Responses managed via {activeJob.ats_source.toUpperCase()}</span>
                </div>

                {/* Badges */}
                <div className="flex flex-wrap items-center gap-2 mt-3 text-xs">
                  {/* Workplace type badge */}
                  <span className={`px-3 py-1 rounded-full font-semibold border ${
                    activeJob.workplace_type === 'Remote'
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800'
                      : activeJob.workplace_type === 'Hybrid'
                      ? 'bg-indigo-50 text-indigo-800 border-indigo-200 dark:bg-indigo-950/40 dark:text-indigo-300 dark:border-indigo-800'
                      : darkMode ? 'bg-[#1e3a5f] text-slate-300 border-[#2a4a6f]' : 'bg-slate-100 text-slate-700 border-slate-200'
                  }`}>
                    {activeJob.workplace_type ? `\u2713 ${activeJob.workplace_type}` : activeJob.remote ? '\u2713 Remote' : '\u2713 On-site / Hybrid'}
                  </span>

                  {/* Employment type badge */}
                  {(activeJob.employment_type || true) && (
                    <span className={`px-3 py-1 rounded-full font-semibold border ${darkMode ? 'bg-[#1e3a5f] text-slate-300 border-[#2a4a6f]' : 'bg-slate-100 text-slate-700 border-slate-200'}`}>
                      {activeJob.employment_type || 'Full-time'}
                    </span>
                  )}

                  {/* Experience level badge */}
                  {activeJob.experience_level && (
                    <span className={`px-3 py-1 rounded-full font-semibold border ${darkMode ? 'bg-[#1e3a5f] text-slate-300 border-[#2a4a6f]' : 'bg-slate-100 text-slate-700 border-slate-200'}`}>
                      {activeJob.experience_level}
                    </span>
                  )}

                  {/* Department / Team badge */}
                  {(activeJob.team || activeJob.department) && (
                    <span className={`px-3 py-1 rounded-full font-medium border ${darkMode ? 'bg-[#1e3a5f] text-slate-300 border-[#2a4a6f]' : 'bg-slate-50 text-slate-600 border-slate-200'}`}>
                      {activeJob.team ? `${activeJob.department ? `${activeJob.department} \u2022 ` : ''}${activeJob.team}` : activeJob.department}
                    </span>
                  )}

                  {/* Salary badge */}
                  {activeJob.salary && activeJob.salary !== 'Not listed' && (
                    <span className="px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 font-semibold border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800">
                      {activeJob.salary}
                    </span>
                  )}

                  {/* Equity badge */}
                  {activeJob.has_equity && (
                    <span className="px-3 py-1 rounded-full bg-amber-50 text-amber-800 font-semibold border border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800">
                      \u2605 Offers Equity
                    </span>
                  )}

                  {/* Secondary locations */}
                  {activeJob.locations && activeJob.locations.length > 1 && (
                    <span className={`px-3 py-1 rounded-full font-medium border ${darkMode ? 'bg-[#1e3a5f] text-slate-400 border-[#2a4a6f]' : 'bg-slate-50 text-slate-600 border-slate-200'}`} title={activeJob.locations.join(', ')}>
                      +{activeJob.locations.length - 1} more locations
                    </span>
                  )}

                  {activeJob.red_flag_verdict && activeJob.red_flag_verdict !== 'clean' && (
                    <span className={`px-3 py-1 rounded-full font-semibold border ${getVerdictColor(activeJob.red_flag_verdict)}`}>
                      {activeJob.red_flag_verdict.replace(/_/g, ' ')}
                    </span>
                  )}
                </div>

                {/* Primary Button Row */}
                <div className="flex flex-wrap items-center gap-2.5 mt-4 pt-2">
                  <a
                    href={activeJob.application_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-6 py-2.5 rounded-full bg-[#0a66c2] hover:bg-[#004182] text-white text-sm font-bold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
                  >
                    <span>Apply</span>
                    <ExternalLink className="w-4 h-4 ml-0.5" />
                  </a>

                  {/* Auto-Apply Supervised Button */}
                  {onAutoApply && (
                    <button
                      onClick={() => onAutoApply(activeJob, false)}
                      disabled={isAutoApplying && activeJobIdAutoApplying === activeJob.id}
                      className="px-5 py-2.5 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold flex items-center gap-2 shadow-xs transition-all cursor-pointer disabled:opacity-60"
                      title="Auto-fill form, upload resume & cover letter, and answer custom questions via Playwright"
                    >
                      {isAutoApplying && activeJobIdAutoApplying === activeJob.id ? (
                        <>
                          <span className="animate-spin text-sm">⟳</span>
                          <span>Auto-Applying...</span>
                        </>
                      ) : (
                        <>
                          <Bot className="w-4 h-4" />
                          <span>Auto-Apply</span>
                        </>
                      )}
                    </button>
                  )}

                  {/* Copy URL */}
                  <button
                    onClick={() => handleCopyUrl(activeJob.application_url)}
                    className={`p-2 rounded-full border transition-all cursor-pointer ${
                      copiedUrl
                        ? 'border-emerald-300 bg-emerald-50 text-emerald-700'
                        : darkMode
                        ? 'border-[#1e3a5f] hover:bg-[#1e3a5f] text-slate-400'
                        : 'border-slate-300 hover:bg-slate-50 text-slate-500'
                    }`}
                    title="Copy application URL"
                  >
                    {copiedUrl ? <Check className="w-4 h-4" /> : <Link className="w-4 h-4" />}
                  </button>

                  <button
                    onClick={() => onTrack(activeJob, activeJob.tracker_status === 'saved' ? 'applied' : 'saved')}
                    className="px-5 py-2 rounded-full border border-[#0a66c2] text-[#0a66c2] hover:bg-blue-50 text-sm font-bold transition-all cursor-pointer"
                  >
                    {activeJob.tracker_status ? `Stage: ${activeJob.tracker_status}` : 'Save'}
                  </button>

                  <button
                    onClick={() => onTailor(activeJob, false)}
                    disabled={isTailoring && activeJobIdTailoring === activeJob.id}
                    className="px-4 py-2 rounded-full bg-purple-700 hover:bg-purple-800 text-white text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer disabled:opacity-50"
                  >
                    {isTailoring && activeJobIdTailoring === activeJob.id ? (
                      <span className="animate-spin text-xs">\u27f3</span>
                    ) : (
                      <Sparkles className="w-3.5 h-3.5" />
                    )}
                    <span>{activeJob.has_tailored_resume ? 'Re-Tailor' : 'Tailor Resume'}</span>
                  </button>

                  <button
                    onClick={() => onTailor(activeJob, true)}
                    disabled={isTailoring && activeJobIdTailoring === activeJob.id}
                    className={`px-4 py-2 rounded-full border text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                      darkMode ? 'border-[#1e3a5f] hover:bg-[#1e3a5f] text-slate-300' : 'border-slate-300 hover:bg-slate-50 text-slate-700'
                    }`}
                  >
                    <FileText className={`w-3.5 h-3.5 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`} />
                    <span>Cover Letter</span>
                  </button>
                </div>
              </div>

              {/* Premium Match Box */}
              <div className="bg-[#fffbf2] border border-[#f5dfb8] rounded-xl p-4 sm:p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-3.5 h-3.5 rounded-xs bg-[#c37d16] flex items-center justify-center text-[10px] text-white font-bold">
                      in
                    </span>
                    <span className="text-xs font-bold text-[#b27800] uppercase tracking-wider">
                      Premium Match Intelligence
                    </span>
                  </div>

                  <span className="text-xs font-bold text-slate-700">
                    Match Confidence: <span className="text-[#0a66c2]">{Math.round((activeJob.score || 0.5) * 100)}%</span>
                  </span>
                </div>

                <div>
                  <h4 className="text-base font-bold text-slate-900">
                    Job match is{' '}
                    <span className="text-[#0a66c2]">
                      {Math.round((activeJob.score || 0.5) * 100) >= 70
                        ? 'high'
                        : Math.round((activeJob.score || 0.5) * 100) >= 50
                        ? 'medium'
                        : 'moderate'}
                    </span>
                    , review match details
                  </h4>
                  <p className="text-xs text-slate-600 mt-1">
                    Your profile and resume match several of the key requirements for this position.
                  </p>
                </div>

                {activeJob.role_fit && (
                  <div className="bg-white/80 p-3 rounded-lg border border-[#f5dfb8] text-xs text-slate-700 italic">
                    "{activeJob.role_fit}"
                  </div>
                )}

                {/* Sub Action Pills */}
                <div className="flex flex-wrap items-center gap-2 pt-1">
                  <button
                    onClick={() => setActiveTab('validation')}
                    className="px-3.5 py-1.5 rounded-full bg-white hover:bg-slate-50 border border-slate-300 text-xs font-semibold text-slate-800 flex items-center gap-1.5 cursor-pointer shadow-2xs"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-[#c37d16]" />
                    <span>Show match details</span>
                  </button>

                  <button
                    onClick={() => onTailor(activeJob, false)}
                    className="px-3.5 py-1.5 rounded-full bg-white hover:bg-slate-50 border border-slate-300 text-xs font-semibold text-slate-800 flex items-center gap-1.5 cursor-pointer shadow-2xs"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-[#c37d16]" />
                    <span>Tailor my resume</span>
                  </button>

                  {activeJob.key_gaps && activeJob.key_gaps.length > 0 && (
                    <span className="text-xs text-slate-500 font-medium ml-1">
                      {activeJob.key_gaps.length} skill gaps detected
                    </span>
                  )}
                </div>

                {/* Missing Keywords */}
                {activeJob.key_gaps && activeJob.key_gaps.length > 0 && (
                  <div className="pt-2 border-t border-[#f5dfb8]/60 flex flex-wrap gap-1.5">
                    {activeJob.key_gaps.map((gap, i) => (
                      <span
                        key={i}
                        className="text-[11px] bg-amber-100/60 text-amber-900 border border-amber-300/60 px-2 py-0.5 rounded-full font-medium"
                      >
                        + {gap}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Subtabs Bar */}
              <div className={`flex items-center gap-1 border-b pb-2 overflow-x-auto ${darkMode ? 'border-[#1e3a5f]' : 'border-slate-200'}`}>
                {([
                  { id: 'jd' as DetailTab, label: 'About the Job', show: true },
                  { id: 'red_flags' as DetailTab, label: 'Red Flags', show: true, icon: <Flag className="w-3.5 h-3.5" />, count: tailoredOutput?.red_flags?.total },
                  { id: 'company' as DetailTab, label: 'Company', show: true, icon: <Building2 className="w-3.5 h-3.5" /> },
                  { id: 'resume' as DetailTab, label: 'Tailored Resume', show: activeJob.has_tailored_resume, icon: <CheckCircle2 className="w-3.5 h-3.5" /> },
                  { id: 'diff' as DetailTab, label: 'Diff', show: activeJob.has_tailored_resume && !!tailoredOutput?.change_summary, icon: <GitCompare className="w-3.5 h-3.5" /> },
                  { id: 'cover_letter' as DetailTab, label: 'Cover Letter', show: activeJob.has_tailored_resume, icon: <FileText className="w-3.5 h-3.5" /> },
                  { id: 'validation' as DetailTab, label: 'ATS Report', show: activeJob.has_tailored_resume, icon: <ShieldCheck className="w-3.5 h-3.5" /> },
                ]).filter(t => t.show).map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`px-3 py-2 text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer whitespace-nowrap ${
                      activeTab === tab.id
                        ? darkMode
                          ? 'bg-[#1e3a5f] text-[#0a66c2] border-b-2 border-b-[#0a66c2]'
                          : 'bg-slate-100 text-slate-900 border-b-2 border-b-slate-900'
                        : darkMode
                        ? 'text-slate-400 hover:text-slate-200'
                        : 'text-slate-500 hover:text-slate-900'
                    }`}
                  >
                    {tab.icon}
                    {tab.label}
                    {tab.count !== undefined && tab.count > 0 && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 font-bold">{tab.count}</span>
                    )}
                  </button>
                ))}
              </div>

              {/* TAB CONTENT: JD */}
              {activeTab === 'jd' && (
                <div className="space-y-4">
                  <h3 className={`text-lg font-bold ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>About the job</h3>
                  <div
                    className="jd-content"
                    dangerouslySetInnerHTML={{
                      __html: parseAndFormatJD(
                        activeJob.description_html,
                        activeJob.description_text
                      ),
                    }}
                  />
                </div>
              )}

              {/* TAB CONTENT: RED FLAGS */}
              {activeTab === 'red_flags' && (
                <div className="space-y-4">
                  <h3 className={`text-lg font-bold ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>Red Flag Analysis</h3>

                  {tailoredOutput?.red_flags ? (
                    <div className="space-y-4">
                      {/* Summary Bar */}
                      <div className={`p-4 rounded-xl border flex items-center justify-between ${getVerdictColor(tailoredOutput.red_flags.verdict)}`}>
                        <div className="flex items-center gap-3">
                          <Flag className="w-5 h-5" />
                          <div>
                            <p className="text-sm font-bold">Verdict: {tailoredOutput.red_flags.verdict.replace(/_/g, ' ')}</p>
                            <p className="text-xs mt-0.5">{tailoredOutput.red_flags.total} total flags ({tailoredOutput.red_flags.critical} critical, {tailoredOutput.red_flags.warnings} warnings)</p>
                          </div>
                        </div>
                      </div>

                      {/* Flag Cards */}
                      <div className="space-y-2">
                        {tailoredOutput.red_flags.flags.map((flag, idx) => (
                          <div key={idx} className={`p-4 rounded-xl border ${getSeverityColor(flag.severity)}`}>
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs font-bold uppercase tracking-wider">{flag.category}</span>
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getSeverityColor(flag.severity)}`}>
                                {flag.severity.toUpperCase()}
                              </span>
                            </div>
                            <p className="text-sm font-semibold mb-1">{flag.signal}</p>
                            <p className="text-xs opacity-80">{flag.evidence}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className={`p-8 rounded-xl border text-center ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-slate-50 border-slate-200'}`}>
                      <Flag className={`w-8 h-8 mx-auto mb-2 ${darkMode ? 'text-slate-500' : 'text-slate-300'}`} />
                      <p className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                        Red flag analysis will appear here after tailoring. Click "Tailor Resume" to generate.
                      </p>
                    </div>
                  )}

                  {/* Legacy red_flags from JobListing */}
                  {activeJob.red_flags && activeJob.red_flags.length > 0 && !tailoredOutput?.red_flags && (
                    <div className="space-y-2">
                      <h4 className={`text-sm font-bold ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>Detected Concerns</h4>
                      {activeJob.red_flags.map((rf, i) => (
                        <div key={i} className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-800 flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 shrink-0" />
                          {rf}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB CONTENT: COMPANY BRIEF */}
              {activeTab === 'company' && (
                <div className="space-y-4">
                  <h3 className={`text-lg font-bold ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>Company Research</h3>

                  {tailoredOutput?.company_brief ? (
                    <div className="space-y-4">
                      {/* Company Header */}
                      <div className={`p-5 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
                        <h4 className={`text-base font-bold ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>
                          {tailoredOutput.company_brief.company_name}
                        </h4>
                        <div className="flex flex-wrap gap-2 mt-2">
                          <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 font-semibold">
                            {tailoredOutput.company_brief.industry}
                          </span>
                          <span className="text-[11px] px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200 font-semibold">
                            {tailoredOutput.company_brief.stage}
                          </span>
                          <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 font-semibold">
                            ~{tailoredOutput.company_brief.estimated_size} employees
                          </span>
                        </div>
                      </div>

                      {/* Info Grid */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
                          <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Known For</h5>
                          <p className={`text-sm ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>{tailoredOutput.company_brief.known_for}</p>
                        </div>
                        <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
                          <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Funding</h5>
                          <p className={`text-sm ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>{tailoredOutput.company_brief.funding_status}</p>
                        </div>
                        <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
                          <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Glassdoor Sentiment</h5>
                          <p className={`text-sm ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>{tailoredOutput.company_brief.glassdoor_sentiment}</p>
                        </div>
                        <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
                          <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Verdict</h5>
                          <p className={`text-sm font-semibold ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>{tailoredOutput.company_brief.verdict}</p>
                        </div>
                      </div>

                      {/* Tech Stack */}
                      {tailoredOutput.company_brief.tech_stack_signals.length > 0 && (
                        <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
                          <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Tech Stack Signals</h5>
                          <div className="flex flex-wrap gap-1.5">
                            {tailoredOutput.company_brief.tech_stack_signals.map((t, i) => (
                              <span key={i} className="text-[11px] px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 font-medium">
                                {t}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Culture Signals */}
                      {tailoredOutput.company_brief.culture_signals.length > 0 && (
                        <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
                          <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Culture Signals</h5>
                          <div className="flex flex-wrap gap-1.5">
                            {tailoredOutput.company_brief.culture_signals.map((c, i) => (
                              <span key={i} className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
                                {c}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Notable Facts */}
                      {tailoredOutput.company_brief.notable_facts.length > 0 && (
                        <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
                          <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Notable Facts</h5>
                          <ul className="space-y-1">
                            {tailoredOutput.company_brief.notable_facts.map((f, i) => (
                              <li key={i} className={`text-xs flex items-start gap-2 ${darkMode ? 'text-slate-200' : 'text-slate-700'}`}>
                                <Info className="w-3.5 h-3.5 text-blue-500 shrink-0 mt-0.5" />
                                {f}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Potential Concerns */}
                      {tailoredOutput.company_brief.potential_concerns.length > 0 && (
                        <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-amber-50 border-amber-200'}`}>
                          <h5 className="text-xs font-bold uppercase tracking-wider mb-2 text-amber-700">Potential Concerns</h5>
                          <ul className="space-y-1">
                            {tailoredOutput.company_brief.potential_concerns.map((c, i) => (
                              <li key={i} className="text-xs text-amber-800 flex items-start gap-2">
                                <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                                {c}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className={`p-8 rounded-xl border text-center ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-slate-50 border-slate-200'}`}>
                      <Building2 className={`w-8 h-8 mx-auto mb-2 ${darkMode ? 'text-slate-500' : 'text-slate-300'}`} />
                      <p className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                        Company research will appear here after tailoring. Click "Tailor Resume" to generate.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* TAB CONTENT: TAILORED RESUME */}
              {activeTab === 'resume' && (
                <div className="space-y-4">
                  <div className={`flex items-center justify-between p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-slate-50 border-slate-200'}`}>
                    <div>
                      <h4 className={`text-sm font-bold ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>Custom Targeted Resume</h4>
                      <p className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                        Optimized for {activeJob.company}'s ATS keyword filter with verified page fit.
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <a
                        href={`/api/jobs/${activeJob.id}/pdf`}
                        download={`Resume_${activeJob.company}_${activeJob.title}.pdf`}
                        className="px-4 py-2 rounded-full bg-[#057642] hover:bg-[#046237] text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
                      >
                        <Download className="w-3.5 h-3.5" /> Download PDF
                      </a>
                      <a
                        href={`/api/jobs/${activeJob.id}/html`}
                        target="_blank"
                        rel="noreferrer"
                        className={`px-4 py-2 rounded-full border text-xs font-semibold cursor-pointer ${
                          darkMode ? 'border-[#1e3a5f] hover:bg-[#16213e] text-slate-300' : 'border-slate-300 hover:bg-white text-slate-700'
                        }`}
                      >
                        Open HTML
                      </a>
                    </div>
                  </div>

                  <div className={`w-full h-[650px] rounded-xl overflow-hidden border shadow-xs ${darkMode ? 'border-[#2a4a6f] bg-[#1e3a5f]' : 'border-slate-200 bg-white'}`}>
                    <iframe
                      src={`/api/jobs/${activeJob.id}/pdf`}
                      className="w-full h-full"
                      title="Tailored Resume Preview"
                    />
                  </div>
                </div>
              )}

              {/* TAB CONTENT: DIFF */}
              {activeTab === 'diff' && tailoredOutput?.change_summary && (
                <div className="space-y-4">
                  <h3 className={`text-lg font-bold ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>Resume Changes Diff</h3>

                  {(() => {
                    const { removed, added, keywords } = parseDiffFromChangeSummary(tailoredOutput.change_summary || '')
                    return (
                      <div className="space-y-4">
                        {/* Keywords Injected */}
                        {keywords.length > 0 && (
                          <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
                            <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Keywords Highlighted</h5>
                            <div className="flex flex-wrap gap-1.5">
                              {keywords.map((kw, i) => (
                                <span key={i} className="diff-keyword text-[11px] px-2 py-0.5 rounded-full">
                                  {kw}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Diff View */}
                        <div className={`rounded-xl border overflow-hidden ${darkMode ? 'border-[#2a4a6f]' : 'border-slate-200'}`}>
                          {removed.length > 0 && (
                            <div className="border-b border-slate-200">
                              <div className="px-4 py-2 bg-red-50 text-xs font-bold text-red-700 border-b border-red-200">Removed / Replaced</div>
                              <div className="p-4 space-y-1">
                                {removed.map((line, i) => (
                                  <div key={i} className="diff-remove text-xs py-1 px-2 rounded">{line}</div>
                                ))}
                              </div>
                            </div>
                          )}
                          {added.length > 0 && (
                            <div>
                              <div className="px-4 py-2 bg-green-50 text-xs font-bold text-green-700 border-b border-green-200">Added / Updated</div>
                              <div className="p-4 space-y-1">
                                {added.map((line, i) => (
                                  <div key={i} className="diff-add text-xs py-1 px-2 rounded">{line}</div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Raw Change Summary */}
                        <details className={`rounded-xl border ${darkMode ? 'border-[#2a4a6f]' : 'border-slate-200'}`}>
                          <summary className={`px-4 py-3 text-xs font-semibold cursor-pointer ${darkMode ? 'text-slate-300' : 'text-slate-600'}`}>
                            View Raw Change Summary
                          </summary>
                          <div className={`px-4 pb-4 text-xs font-mono whitespace-pre-wrap leading-relaxed ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>
                            {tailoredOutput.change_summary}
                          </div>
                        </details>
                      </div>
                    )
                  })()}
                </div>
              )}

              {/* TAB CONTENT: COVER LETTER */}
              {activeTab === 'cover_letter' && (
                <div className="space-y-4">
                  <div className={`flex items-center justify-between p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-slate-50 border-slate-200'}`}>
                    <div>
                      <h4 className={`text-sm font-bold ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>Custom Cover Letter</h4>
                      <p className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                        Tailored addressing {activeJob.company}'s specific challenges and team mission.
                      </p>
                    </div>
                    {coverLetterText && (
                      <button
                        onClick={() => handleCopyCoverLetter(coverLetterText)}
                        className="px-4 py-2 rounded-full bg-[#0a66c2] hover:bg-[#004182] text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
                      >
                        {copiedCoverLetter ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copiedCoverLetter ? 'Copied!' : 'Copy to Clipboard'}</span>
                      </button>
                    )}
                  </div>

                  <div className={`p-6 rounded-xl border whitespace-pre-line text-sm leading-relaxed font-serif shadow-xs ${
                    darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f] text-slate-200' : 'bg-white border-slate-200 text-slate-800'
                  }`}>
                    {coverLetterText || (
                      <div className={`text-center py-10 ${darkMode ? 'text-slate-400' : 'text-slate-400'}`}>
                        <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p>No cover letter generated yet.</p>
                        <button
                          onClick={() => onTailor(activeJob, true)}
                          className="mt-3 px-4 py-1.5 rounded-full bg-[#0a66c2] text-white text-xs font-semibold cursor-pointer"
                        >
                          Generate Cover Letter
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* TAB CONTENT: ATS MATCH REPORT */}
              {activeTab === 'validation' && (
                <div className="space-y-4">
                  <div className={`p-5 rounded-xl border space-y-3 ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
                    <h4 className={`text-sm font-bold uppercase tracking-wider flex items-center gap-2 ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>
                      <ShieldCheck className="w-4 h-4 text-[#057642]" /> Automated ATS Inspection
                    </h4>
                    {tailoredOutput?.validation_report ? (
                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          <span className={`text-xs font-semibold ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>
                            Status:{' '}
                            <span
                              className={
                                tailoredOutput.validation_report.passed
                                  ? 'text-[#057642] font-bold'
                                  : 'text-amber-700 font-bold'
                              }
                            >
                              {tailoredOutput.validation_report.passed
                                ? '9 / 9 Automated ATS Checks Passed'
                                : 'Needs Minor Review'}
                            </span>
                          </span>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                          {tailoredOutput.validation_report.checks?.map((chk: any, idx: number) => (
                            <div
                              key={idx}
                              className={`p-3 rounded-lg border flex items-center gap-2.5 ${darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-slate-50 border-slate-200'}`}
                            >
                              {chk.passed ? (
                                <CheckCircle2 className="w-4 h-4 text-[#057642] shrink-0" />
                              ) : (
                                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                              )}
                              <span className={`font-medium ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>{chk.name}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <p className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>Validation report not yet generated.</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : jobs.length === 0 ? (
            /* Empty state when no jobs at all */
            <div className="h-full flex flex-col items-center justify-center p-8">
              <Briefcase className={`w-16 h-16 mb-4 ${darkMode ? 'text-slate-600' : 'text-slate-200'}`} />
              <p className={`font-bold text-lg ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>No jobs scanned yet</p>
              <p className={`text-sm mt-2 text-center max-w-sm ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                Configure your ATS board links in Settings, then click "Scan ATS Boards" to discover matching roles.
              </p>
            </div>
          ) : (
            /* Skeleton / placeholder when no job selected */
            <SkeletonPanel />
          )}
        </div>
      </div>
    </div>
  )
}
