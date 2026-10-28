import React, { useState, useMemo } from 'react'
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
} from 'lucide-react'
import { JobListing, JobOutput } from '../types'

interface JobSplitViewProps {
  jobs: JobListing[]
  selectedJob: JobListing | null
  onSelectJob: (job: JobListing) => void
  onTailor: (job: JobListing, coverLetter: boolean) => Promise<void>
  onTrack: (job: JobListing, status: string) => void
  tailoredOutput: JobOutput | null
  isTailoring: boolean
  activeJobIdTailoring: string | null
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
}) => {
  // Filter states
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedPlatform, setSelectedPlatform] = useState<string>('all')
  const [remoteOnly, setRemoteOnly] = useState(false)
  const [minScoreFilter, setMinScoreFilter] = useState<number>(0)
  const [tailoredOnly, setTailoredOnly] = useState(false)
  const [activeTab, setActiveTab] = useState<'jd' | 'resume' | 'cover_letter' | 'validation'>('jd')
  const [copiedCoverLetter, setCopiedCoverLetter] = useState(false)

  // Unique ATS platforms
  const platforms = useMemo(() => {
    const set = new Set<string>()
    jobs.forEach((j) => {
      if (j.ats_source) set.add(j.ats_source)
    })
    return Array.from(set)
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
      if (remoteOnly && !job.remote) return false
      if (minScoreFilter > 0 && (job.score || 0) < minScoreFilter) return false
      if (tailoredOnly && !job.has_tailored_resume) return false
      return true
    })
  }, [jobs, searchQuery, selectedPlatform, remoteOnly, minScoreFilter, tailoredOnly])

  // Auto-select first job if none selected
  const activeJob = selectedJob || filteredJobs[0] || null

  const handleCopyCoverLetter = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedCoverLetter(true)
    setTimeout(() => setCopiedCoverLetter(false), 2000)
  }

  const parseAndFormatJD = (rawHtml?: string, rawText?: string): string => {
    if (!rawHtml && !rawText) return '<p class="text-slate-500">No description provided.</p>'

    let str = rawHtml || rawText || ''

    // Decode HTML entities if escaped (e.g. &lt;div&gt;)
    if (str.includes('&lt;') || str.includes('&gt;') || str.includes('&quot;') || str.includes('&amp;')) {
      const parser = new DOMParser()
      const doc = parser.parseFromString(str, 'text/html')
      str = doc.body.innerHTML || doc.documentElement.textContent || str
      if (str.includes('&lt;') && str.includes('&gt;')) {
        const doc2 = parser.parseFromString(str, 'text/html')
        str = doc2.body.innerHTML || str
      }
    }

    // Strip inline font-family, font-size, and background styles from external ATS boards
    str = str.replace(/style="[^"]*"/gi, '')
    str = str.replace(/style='[^']*'/gi, '')

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

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] overflow-hidden bg-[#f4f2ee]">
      {/* =========================================================================
          TOP FILTER BAR (Exact LinkedIn style)
         ========================================================================= */}
      <div className="bg-white border-b border-slate-200 px-4 sm:px-6 py-2.5 flex flex-wrap items-center justify-between gap-3 shrink-0 shadow-xs">
        <div className="flex flex-wrap items-center gap-2 flex-1">
          {/* Search Input with LinkedIn Pill Style */}
          <div className="relative min-w-[220px] max-w-xs">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by title, skill, or company"
              className="w-full bg-[#edf3f8] hover:bg-[#e4ebf2] focus:bg-white border border-transparent focus:border-[#0a66c2] rounded-full pl-9 pr-4 py-1.5 text-xs text-slate-900 placeholder-slate-500 focus:outline-none transition-all"
            />
          </div>

          {/* Active Filter Pill (LinkedIn Green) */}
          <button
            onClick={() => {}}
            className="px-3.5 py-1.5 rounded-full text-xs font-semibold bg-[#01754f] text-white transition-all cursor-pointer shadow-xs"
          >
            Jobs ▾
          </button>

          {/* Remote Filter Pill */}
          <button
            onClick={() => setRemoteOnly(!remoteOnly)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer ${
              remoteOnly
                ? 'bg-[#01754f] text-white border-transparent'
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            Remote {remoteOnly && '✓'}
          </button>

          {/* Tailored Only Filter Pill */}
          <button
            onClick={() => setTailoredOnly(!tailoredOnly)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer ${
              tailoredOnly
                ? 'bg-[#01754f] text-white border-transparent'
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            Tailored Only {tailoredOnly && '✓'}
          </button>

          {/* ATS Source Dropdown Pill */}
          <select
            value={selectedPlatform}
            onChange={(e) => setSelectedPlatform(e.target.value)}
            className="bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 rounded-full px-3.5 py-1.5 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-[#0a66c2] cursor-pointer"
          >
            <option value="all">All ATS Platforms</option>
            {platforms.map((p) => (
              <option key={p} value={p}>
                {p.toUpperCase()}
              </option>
            ))}
          </select>

          {/* Match Score Dropdown Pill */}
          <select
            value={minScoreFilter}
            onChange={(e) => setMinScoreFilter(parseFloat(e.target.value))}
            className="bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 rounded-full px-3.5 py-1.5 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-[#0a66c2] cursor-pointer"
          >
            <option value={0}>Experience / Match: All</option>
            <option value={0.7}>70%+ Strong Match</option>
            <option value={0.5}>50%+ Medium Match</option>
            <option value={0.4}>40%+ Good Match</option>
          </select>

          {(searchQuery || remoteOnly || tailoredOnly || selectedPlatform !== 'all' || minScoreFilter > 0) && (
            <button
              onClick={() => {
                setSearchQuery('')
                setRemoteOnly(false)
                setTailoredOnly(false)
                setSelectedPlatform('all')
                setMinScoreFilter(0)
              }}
              className="text-xs text-[#0a66c2] hover:text-[#004182] font-semibold px-2 py-1 cursor-pointer"
            >
              Reset filters
            </button>
          )}
        </div>

        {/* Results Count (LinkedIn subhead) */}
        <div className="text-xs text-slate-600 font-medium shrink-0 flex items-center gap-1.5">
          <span>{filteredJobs.length} results</span>
        </div>
      </div>

      {/* =========================================================================
          MAIN SPLIT VIEW (LinkedIn Layout)
         ========================================================================= */}
      <div className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-5 flex gap-5 overflow-hidden">
        {/* -----------------------------------------------------------------------
            LEFT COLUMN: Scrollable Job Listings
           ----------------------------------------------------------------------- */}
        <div className="w-full md:w-[380px] lg:w-[410px] xl:w-[430px] bg-white rounded-xl border border-slate-200 overflow-y-auto shrink-0 divide-y divide-slate-100 shadow-xs">
          {filteredJobs.length === 0 ? (
            <div className="p-10 text-center text-slate-500">
              <Briefcase className="w-10 h-10 mx-auto mb-2 text-slate-300" />
              <p className="font-semibold text-slate-800">No matching jobs</p>
              <p className="text-xs text-slate-500 mt-1">Try resetting or broadening your filters.</p>
            </div>
          ) : (
            filteredJobs.map((job) => {
              const isSelected = activeJob?.id === job.id
              const matchPct = Math.round((job.score || 0.5) * 100)
              const avatarColor = getAvatarColor(job.company)

              return (
                <div
                  key={job.id}
                  onClick={() => onSelectJob(job)}
                  className={`p-4 transition-all cursor-pointer relative flex gap-3.5 hover:bg-slate-50 ${
                    isSelected
                      ? 'bg-[#edf3f8]/70 border-l-4 border-l-[#0a66c2]'
                      : 'border-l-4 border-l-transparent'
                  }`}
                >
                  {/* Company Logo Square */}
                  <div
                    className={`w-12 h-12 rounded-lg ${avatarColor} flex items-center justify-center text-white font-bold text-sm shrink-0 shadow-xs`}
                  >
                    {job.company.substring(0, 2).toUpperCase()}
                  </div>

                  {/* Job Summary */}
                  <div className="flex-1 min-w-0">
                    <h4
                      className={`text-sm font-semibold truncate ${
                        isSelected ? 'text-[#0a66c2]' : 'text-slate-900 hover:text-[#0a66c2]'
                      }`}
                    >
                      {job.title}
                    </h4>

                    <p className="text-xs text-slate-700 font-normal mt-0.5">{job.company}</p>

                    <p className="text-xs text-slate-500 mt-0.5 truncate">
                      {job.location || 'Remote'} {job.remote && '(Remote)'}
                    </p>

                    {job.salary && (
                      <p className="text-xs text-slate-600 font-medium mt-1 truncate">
                        {job.salary}
                      </p>
                    )}

                    {/* LinkedIn Style Tags & Status */}
                    <div className="flex items-center gap-2 mt-2 pt-1 border-t border-slate-100 text-[11px]">
                      {job.has_tailored_resume ? (
                        <span className="flex items-center gap-1 text-[#057642] font-semibold">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Tailored
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-[#057642] font-medium">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Actively reviewing
                        </span>
                      )}

                      <span className="text-slate-300">&bull;</span>

                      <span
                        className={`font-semibold px-2 py-0.2 rounded-full ${
                          matchPct >= 70
                            ? 'bg-emerald-50 text-emerald-700'
                            : matchPct >= 50
                            ? 'bg-blue-50 text-blue-700'
                            : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {matchPct}% Match
                      </span>
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* -----------------------------------------------------------------------
            RIGHT COLUMN: LinkedIn-Style Detailed Job View
           ----------------------------------------------------------------------- */}
        <div className="flex-1 bg-white rounded-xl border border-slate-200 overflow-y-auto shadow-xs flex flex-col">
          {activeJob ? (
            <div className="p-6 space-y-6">
              {/* Header section with Company Logo & Actions */}
              <div>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3.5">
                    <div
                      className={`w-14 h-14 rounded-lg ${getAvatarColor(
                        activeJob.company
                      )} flex items-center justify-center text-white font-bold text-lg shadow-xs`}
                    >
                      {activeJob.company.substring(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <span className="text-sm font-semibold text-slate-700 hover:text-[#0a66c2] cursor-pointer">
                        {activeJob.company}
                      </span>
                      <h2 className="text-2xl font-bold text-slate-900 tracking-tight mt-0.5">
                        {activeJob.title}
                      </h2>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 text-slate-400">
                    <button className="p-2 hover:bg-slate-100 rounded-full transition-colors cursor-pointer text-slate-600">
                      <MoreHorizontal className="w-5 h-5" />
                    </button>
                  </div>
                </div>

                {/* Metadata Line */}
                <div className="flex flex-wrap items-center gap-2 mt-3 text-xs text-slate-500">
                  <span className="font-medium text-slate-700">{activeJob.location || 'Remote'}</span>
                  <span>&bull;</span>
                  {activeJob.posted_date && (
                    <>
                      <span>Posted {activeJob.posted_date}</span>
                      <span>&bull;</span>
                    </>
                  )}
                  <span>Responses managed via {activeJob.ats_source.toUpperCase()}</span>
                </div>

                {/* Badges / Attributes */}
                <div className="flex flex-wrap items-center gap-2 mt-3 text-xs">
                  <span className="px-3 py-1 rounded-full bg-slate-100 text-slate-700 font-semibold border border-slate-200">
                    {activeJob.remote ? '✓ Remote' : '✓ On-site / Hybrid'}
                  </span>
                  <span className="px-3 py-1 rounded-full bg-slate-100 text-slate-700 font-semibold border border-slate-200">
                    Full-time
                  </span>
                  {activeJob.salary && (
                    <span className="px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 font-semibold border border-emerald-200">
                      💰 {activeJob.salary}
                    </span>
                  )}
                </div>

                {/* Primary Button Row (Apply & Save) */}
                <div className="flex flex-wrap items-center gap-2.5 mt-4 pt-2">
                  {/* LinkedIn Blue Apply Button */}
                  <a
                    href={activeJob.application_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-6 py-2.5 rounded-full bg-[#0a66c2] hover:bg-[#004182] text-white text-sm font-bold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
                  >
                    <span>Apply</span>
                    <ExternalLink className="w-4 h-4 ml-0.5" />
                  </a>

                  {/* Save to Pipeline Button */}
                  <button
                    onClick={() => onTrack(activeJob, activeJob.tracker_status === 'saved' ? 'applied' : 'saved')}
                    className="px-5 py-2 rounded-full border border-[#0a66c2] text-[#0a66c2] hover:bg-blue-50 text-sm font-bold transition-all cursor-pointer"
                  >
                    {activeJob.tracker_status ? `Stage: ${activeJob.tracker_status}` : 'Save'}
                  </button>

                  {/* Tailor Resume Button */}
                  <button
                    onClick={() => onTailor(activeJob, false)}
                    disabled={isTailoring && activeJobIdTailoring === activeJob.id}
                    className="px-4 py-2 rounded-full bg-purple-700 hover:bg-purple-800 text-white text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer disabled:opacity-50"
                  >
                    {isTailoring && activeJobIdTailoring === activeJob.id ? (
                      <span className="animate-spin text-xs">⟳</span>
                    ) : (
                      <Sparkles className="w-3.5 h-3.5" />
                    )}
                    <span>{activeJob.has_tailored_resume ? 'Re-Tailor' : 'Tailor Resume'}</span>
                  </button>

                  {/* Create Cover Letter Button */}
                  <button
                    onClick={() => onTailor(activeJob, true)}
                    disabled={isTailoring && activeJobIdTailoring === activeJob.id}
                    className="px-4 py-2 rounded-full border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer"
                  >
                    <FileText className="w-3.5 h-3.5 text-slate-500" />
                    <span>Cover Letter</span>
                  </button>
                </div>
              </div>

              {/* LinkedIn Premium Style Match Box (Exact Replica) */}
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

                {/* Sub Action Pills inside Premium Box */}
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

                {/* Missing Keywords Pills */}
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
              <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
                <button
                  onClick={() => setActiveTab('jd')}
                  className={`px-4 py-2 text-xs font-bold rounded-lg transition-colors cursor-pointer ${
                    activeTab === 'jd'
                      ? 'bg-slate-100 text-slate-900 border-b-2 border-b-slate-900'
                      : 'text-slate-500 hover:text-slate-900'
                  }`}
                >
                  About the job
                </button>

                {activeJob.has_tailored_resume && (
                  <>
                    <button
                      onClick={() => setActiveTab('resume')}
                      className={`px-4 py-2 text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer ${
                        activeTab === 'resume'
                          ? 'bg-slate-100 text-[#057642] border-b-2 border-b-[#057642]'
                          : 'text-slate-500 hover:text-slate-900'
                      }`}
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" /> Tailored Resume (PDF)
                    </button>

                    <button
                      onClick={() => setActiveTab('cover_letter')}
                      className={`px-4 py-2 text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer ${
                        activeTab === 'cover_letter'
                          ? 'bg-slate-100 text-purple-700 border-b-2 border-b-purple-700'
                          : 'text-slate-500 hover:text-slate-900'
                      }`}
                    >
                      <FileText className="w-3.5 h-3.5" /> Cover Letter
                    </button>

                    <button
                      onClick={() => setActiveTab('validation')}
                      className={`px-4 py-2 text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer ${
                        activeTab === 'validation'
                          ? 'bg-slate-100 text-[#0a66c2] border-b-2 border-b-[#0a66c2]'
                          : 'text-slate-500 hover:text-slate-900'
                      }`}
                    >
                      <ShieldCheck className="w-3.5 h-3.5" /> ATS Match Report
                    </button>
                  </>
                )}
              </div>

              {/* TAB CONTENT: JD */}
              {activeTab === 'jd' && (
                <div className="space-y-4">
                  <h3 className="text-lg font-bold text-slate-900">About the job</h3>
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

              {/* TAB CONTENT: TAILORED RESUME */}
              {activeTab === 'resume' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-200">
                    <div>
                      <h4 className="text-sm font-bold text-slate-900">Custom Targeted Resume</h4>
                      <p className="text-xs text-slate-500">
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
                        className="px-4 py-2 rounded-full border border-slate-300 hover:bg-white text-slate-700 text-xs font-semibold cursor-pointer"
                      >
                        Open HTML
                      </a>
                    </div>
                  </div>

                  {/* Embedded PDF iframe */}
                  <div className="w-full h-[650px] rounded-xl overflow-hidden border border-slate-200 bg-white shadow-xs">
                    <iframe
                      src={`/api/jobs/${activeJob.id}/pdf`}
                      className="w-full h-full"
                      title="Tailored Resume Preview"
                    />
                  </div>
                </div>
              )}

              {/* TAB CONTENT: COVER LETTER */}
              {activeTab === 'cover_letter' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-200">
                    <div>
                      <h4 className="text-sm font-bold text-slate-900">Custom Cover Letter</h4>
                      <p className="text-xs text-slate-500">
                        Tailored addressing {activeJob.company}'s specific challenges and team mission.
                      </p>
                    </div>
                    {tailoredOutput?.cover_letter && (
                      <button
                        onClick={() => handleCopyCoverLetter(tailoredOutput.cover_letter!)}
                        className="px-4 py-2 rounded-full bg-[#0a66c2] hover:bg-[#004182] text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
                      >
                        {copiedCoverLetter ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copiedCoverLetter ? 'Copied!' : 'Copy to Clipboard'}</span>
                      </button>
                    )}
                  </div>

                  <div className="p-6 rounded-xl border border-slate-200 whitespace-pre-line text-sm text-slate-800 leading-relaxed font-serif bg-white shadow-xs">
                    {tailoredOutput?.cover_letter || (
                      <div className="text-center py-10 text-slate-400">
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
                  <div className="p-5 rounded-xl border border-slate-200 bg-white space-y-3">
                    <h4 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-[#057642]" /> Automated ATS Inspection
                    </h4>
                    {tailoredOutput?.validation_report ? (
                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-slate-700">
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
                              className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center gap-2.5"
                            >
                              {chk.passed ? (
                                <CheckCircle2 className="w-4 h-4 text-[#057642] shrink-0" />
                              ) : (
                                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                              )}
                              <span className="text-slate-800 font-medium">{chk.name}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500">Validation report not yet generated.</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-slate-400 p-8">
              <Briefcase className="w-12 h-12 mb-3 opacity-30 text-slate-300" />
              <p className="font-semibold text-slate-700 text-sm">Select a job from the list</p>
              <p className="text-xs text-slate-400 mt-1">
                View role fit, compensation details, and tailor your application.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
