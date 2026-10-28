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

  // Company avatar fallback color generator
  const getAvatarColor = (name: string) => {
    const colors = [
      'bg-blue-600',
      'bg-indigo-600',
      'bg-purple-600',
      'bg-emerald-600',
      'bg-amber-600',
      'bg-rose-600',
      'bg-teal-600',
    ]
    let hash = 0
    for (let i = 0; i < name.length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash)
    }
    return colors[Math.abs(hash) % colors.length]
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] overflow-hidden">
      {/* =========================================================================
          TOP FILTER BAR (LinkedIn style)
         ========================================================================= */}
      <div className="bg-slate-900/90 border-b border-slate-800 px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex flex-wrap items-center gap-2 flex-1">
          {/* Search Input */}
          <div className="relative min-w-[240px] max-w-xs">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search title, company, skill..."
              className="w-full bg-slate-950/80 border border-slate-700/80 rounded-full pl-9 pr-4 py-1.5 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
            />
          </div>

          {/* Filter Pills */}
          <button
            onClick={() => setRemoteOnly(!remoteOnly)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
              remoteOnly
                ? 'bg-blue-600 text-white border-blue-500 shadow-sm shadow-blue-500/20'
                : 'bg-slate-800/80 hover:bg-slate-700 text-slate-300 border-slate-700'
            }`}
          >
            Remote {remoteOnly && '✓'}
          </button>

          <button
            onClick={() => setTailoredOnly(!tailoredOnly)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
              tailoredOnly
                ? 'bg-emerald-600 text-white border-emerald-500 shadow-sm shadow-emerald-500/20'
                : 'bg-slate-800/80 hover:bg-slate-700 text-slate-300 border-slate-700'
            }`}
          >
            Tailored Only {tailoredOnly && '✓'}
          </button>

          {/* ATS Source Dropdown */}
          <select
            value={selectedPlatform}
            onChange={(e) => setSelectedPlatform(e.target.value)}
            className="bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-full px-3 py-1.5 text-xs font-medium focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer"
          >
            <option value="all">All ATS Platforms</option>
            {platforms.map((p) => (
              <option key={p} value={p}>
                {p.toUpperCase()}
              </option>
            ))}
          </select>

          {/* Match Score Dropdown */}
          <select
            value={minScoreFilter}
            onChange={(e) => setMinScoreFilter(parseFloat(e.target.value))}
            className="bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-full px-3 py-1.5 text-xs font-medium focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer"
          >
            <option value={0}>All Match Scores</option>
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
              className="text-xs text-blue-400 hover:text-blue-300 font-medium px-2 py-1"
            >
              Reset filters
            </button>
          )}
        </div>

        {/* Count Indicator */}
        <div className="text-xs text-slate-400 font-medium shrink-0">
          Showing <span className="text-white font-semibold">{filteredJobs.length}</span> of {jobs.length} jobs
        </div>
      </div>

      {/* =========================================================================
          SPLIT VIEW CONTENT (Left: List | Right: Details)
         ========================================================================= */}
      <div className="flex-1 flex overflow-hidden">
        {/* -----------------------------------------------------------------------
            LEFT COLUMN: Scrollable Job Listings (LinkedIn Style)
           ----------------------------------------------------------------------- */}
        <div className="w-full md:w-[420px] lg:w-[460px] xl:w-[490px] border-r border-slate-800 overflow-y-auto bg-slate-950/60 shrink-0 divide-y divide-slate-800/60">
          {filteredJobs.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              <Briefcase className="w-10 h-10 mx-auto mb-3 opacity-40 text-slate-500" />
              <p className="font-semibold text-white">No jobs match your filters</p>
              <p className="text-xs mt-1 text-slate-400">Try adjusting your search keywords or ATS filters.</p>
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
                  className={`p-4 transition-all cursor-pointer relative flex gap-3.5 hover:bg-slate-900/80 ${
                    isSelected
                      ? 'bg-slate-900/90 border-l-4 border-l-blue-500 pl-3'
                      : 'border-l-4 border-l-transparent'
                  }`}
                >
                  {/* Company Logo / Avatar */}
                  <div
                    className={`w-11 h-11 rounded-xl ${avatarColor} flex items-center justify-center text-white font-bold text-sm shrink-0 shadow-md`}
                  >
                    {job.company.substring(0, 2).toUpperCase()}
                  </div>

                  {/* Job Details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <h4
                        className={`text-sm font-semibold truncate ${
                          isSelected ? 'text-blue-400 font-bold' : 'text-white'
                        }`}
                      >
                        {job.title}
                      </h4>
                      {job.has_tailored_resume && (
                        <span
                          className="shrink-0 p-0.5 rounded-full bg-emerald-500/10 text-emerald-400"
                          title="Tailored Resume Generated"
                        >
                          <CheckCircle2 className="w-4 h-4" />
                        </span>
                      )}
                    </div>

                    <p className="text-xs font-medium text-slate-300 mt-0.5">{job.company}</p>

                    <div className="flex items-center gap-2 mt-1.5 text-xs text-slate-400">
                      <span className="truncate max-w-[150px]">{job.location || 'Remote'}</span>
                      <span>&bull;</span>
                      <span className="uppercase text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 font-semibold border border-slate-700">
                        {job.ats_source}
                      </span>
                    </div>

                    {/* Salary & Match Score Row */}
                    <div className="flex items-center justify-between gap-2 mt-2 pt-1 border-t border-slate-800/40 text-xs">
                      <span className="text-slate-400 text-[11px] truncate max-w-[180px]">
                        {job.salary || 'Salary not listed'}
                      </span>
                      <span
                        className={`font-semibold text-xs px-2 py-0.5 rounded-full ${
                          matchPct >= 70
                            ? 'bg-emerald-500/15 text-emerald-400'
                            : matchPct >= 50
                            ? 'bg-blue-500/15 text-blue-400'
                            : 'bg-slate-800 text-slate-400'
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
            RIGHT COLUMN: Detailed View of Selected Job (LinkedIn Style)
           ----------------------------------------------------------------------- */}
        <div className="flex-1 overflow-y-auto bg-slate-950 p-6">
          {activeJob ? (
            <div className="max-w-4xl mx-auto space-y-6">
              {/* Top Header Card */}
              <div className="glass-panel p-6 rounded-2xl border border-slate-800 shadow-xl space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <div
                      className={`w-14 h-14 rounded-2xl ${getAvatarColor(
                        activeJob.company
                      )} flex items-center justify-center text-white font-extrabold text-xl shadow-lg`}
                    >
                      {activeJob.company.substring(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                        {activeJob.title}
                      </h2>
                      <div className="flex items-center gap-2 mt-1 text-sm text-slate-300">
                        <span className="font-semibold text-blue-400">{activeJob.company}</span>
                        <span>&bull;</span>
                        <span className="text-slate-400">{activeJob.location || 'Remote'}</span>
                        {activeJob.posted_date && (
                          <>
                            <span>&bull;</span>
                            <span className="text-slate-500 text-xs">Posted {activeJob.posted_date}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Status Tag */}
                  {activeJob.has_tailored_resume && (
                    <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5 shadow-sm">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Tailored & Validated
                    </span>
                  )}
                </div>

                {/* Tags Row */}
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 border border-slate-700 font-medium">
                    {activeJob.remote ? 'Remote Work' : 'On-Site / Hybrid'}
                  </span>
                  <span className="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 border border-slate-700 font-medium">
                    {activeJob.ats_source.toUpperCase()} Board
                  </span>
                  {activeJob.salary && (
                    <span className="px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold flex items-center gap-1">
                      <DollarSign className="w-3 h-3" />
                      {activeJob.salary}
                    </span>
                  )}
                  {activeJob.red_flag_count && activeJob.red_flag_count > 0 ? (
                    <span className="px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 font-semibold flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" />
                      {activeJob.red_flag_count} Red Flag Warnings
                    </span>
                  ) : null}
                </div>

                {/* Primary Action Buttons */}
                <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-slate-800/80">
                  {/* Apply Job Link */}
                  <a
                    href={activeJob.application_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold flex items-center gap-2 shadow-lg shadow-blue-600/30 transition-all cursor-pointer"
                  >
                    <span>Apply on ATS</span>
                    <ExternalLink className="w-4 h-4" />
                  </a>

                  {/* Tailor Resume Button */}
                  <button
                    onClick={() => onTailor(activeJob, false)}
                    disabled={isTailoring && activeJobIdTailoring === activeJob.id}
                    className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-sm font-semibold flex items-center gap-2 shadow-lg shadow-purple-600/25 transition-all disabled:opacity-50"
                  >
                    {isTailoring && activeJobIdTailoring === activeJob.id ? (
                      <span className="animate-spin text-sm">⟳</span>
                    ) : (
                      <Sparkles className="w-4 h-4 text-purple-200" />
                    )}
                    <span>{activeJob.has_tailored_resume ? 'Re-Tailor Resume' : 'Tailor Resume'}</span>
                  </button>

                  {/* Create Cover Letter Button */}
                  <button
                    onClick={() => onTailor(activeJob, true)}
                    disabled={isTailoring && activeJobIdTailoring === activeJob.id}
                    className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-semibold flex items-center gap-2 border border-slate-700 transition-all"
                  >
                    <FileText className="w-4 h-4 text-slate-400" />
                    <span>Create Cover Letter</span>
                  </button>

                  {/* Pipeline Stage Dropdown */}
                  <div className="flex items-center gap-2 ml-auto">
                    <span className="text-xs text-slate-400 font-medium">Stage:</span>
                    <select
                      value={activeJob.tracker_status || 'saved'}
                      onChange={(e) => onTrack(activeJob, e.target.value)}
                      className="bg-slate-800 border border-slate-700 text-xs text-slate-200 rounded-lg px-3 py-2 font-medium focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer"
                    >
                      <option value="saved">Saved</option>
                      <option value="applied">Applied</option>
                      <option value="interviewing">Interviewing</option>
                      <option value="offer">Offer</option>
                      <option value="rejected">Rejected</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Match Insight Card (LinkedIn Premium Style) */}
              <div className="p-5 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900/90 to-blue-950/40 border border-blue-500/20 shadow-lg space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-amber-400" />
                    <span className="text-xs font-bold uppercase tracking-wider text-amber-400">
                      HireReady Match Intelligence
                    </span>
                  </div>
                  <span className="text-xs font-extrabold text-blue-400">
                    {Math.round((activeJob.score || 0.5) * 100)}% Overall Fit
                  </span>
                </div>

                <div className="space-y-1.5">
                  <h4 className="text-base font-bold text-white">
                    Job match is{' '}
                    <span className="text-blue-400">
                      {Math.round((activeJob.score || 0.5) * 100) >= 70
                        ? 'Strong'
                        : Math.round((activeJob.score || 0.5) * 100) >= 50
                        ? 'Good'
                        : 'Moderate'}
                    </span>
                    , review match insights
                  </h4>
                  {activeJob.role_fit && (
                    <p className="text-xs text-slate-300 leading-relaxed italic bg-slate-950/60 p-3 rounded-xl border border-slate-800">
                      "{activeJob.role_fit}"
                    </p>
                  )}
                </div>

                {/* Key Gaps / Missing Keywords */}
                {activeJob.key_gaps && activeJob.key_gaps.length > 0 && (
                  <div className="pt-2">
                    <span className="text-xs font-semibold text-slate-400 block mb-1.5">
                      Missing Qualifications / Recommended Keywords:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {activeJob.key_gaps.map((gap, i) => (
                        <span
                          key={i}
                          className="text-xs bg-amber-500/10 text-amber-300 border border-amber-500/20 px-2 py-0.5 rounded-md font-medium"
                        >
                          {gap}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Details & Tailored Assets Tab Bar */}
              <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
                <button
                  onClick={() => setActiveTab('jd')}
                  className={`px-4 py-2 text-xs font-bold rounded-lg transition-colors ${
                    activeTab === 'jd'
                      ? 'bg-slate-800 text-white'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  About the Job (JD)
                </button>

                {activeJob.has_tailored_resume && (
                  <>
                    <button
                      onClick={() => setActiveTab('resume')}
                      className={`px-4 py-2 text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5 ${
                        activeTab === 'resume'
                          ? 'bg-slate-800 text-emerald-400'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" /> Tailored Resume (PDF)
                    </button>

                    <button
                      onClick={() => setActiveTab('cover_letter')}
                      className={`px-4 py-2 text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5 ${
                        activeTab === 'cover_letter'
                          ? 'bg-slate-800 text-purple-400'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <FileText className="w-3.5 h-3.5" /> Cover Letter
                    </button>

                    <button
                      onClick={() => setActiveTab('validation')}
                      className={`px-4 py-2 text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5 ${
                        activeTab === 'validation'
                          ? 'bg-slate-800 text-blue-400'
                          : 'text-slate-400 hover:text-slate-200'
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
                  {/* Red flags alert */}
                  {activeJob.red_flags && activeJob.red_flags.length > 0 && (
                    <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-900/40 space-y-1.5">
                      <span className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                        <AlertTriangle className="w-4 h-4" /> Detected Warning Signals
                      </span>
                      <ul className="list-disc list-inside text-xs text-amber-200/90 space-y-1">
                        {activeJob.red_flags.map((flag, idx) => (
                          <li key={idx}>{flag}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="glass-panel p-6 rounded-2xl border border-slate-800">
                    <h3 className="text-sm font-bold text-white mb-4 uppercase tracking-wider">
                      About the Role
                    </h3>
                    <div
                      className="prose prose-invert max-w-none text-xs text-slate-300 leading-relaxed space-y-3"
                      dangerouslySetInnerHTML={{
                        __html:
                          activeJob.description_html ||
                          activeJob.description_text ||
                          'No description provided.',
                      }}
                    />
                  </div>
                </div>
              )}

              {/* TAB CONTENT: TAILORED RESUME */}
              {activeTab === 'resume' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between glass-panel p-4 rounded-xl border border-slate-800">
                    <div>
                      <h4 className="text-sm font-bold text-white">Targeted Resume Compiled</h4>
                      <p className="text-xs text-slate-400">
                        Tailored specifically to highlight relevant achievements for this JD.
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <a
                        href={`/api/jobs/${activeJob.id}/pdf`}
                        download={`Resume_${activeJob.company}_${activeJob.title}.pdf`}
                        className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md transition-all"
                      >
                        <Download className="w-3.5 h-3.5" /> Download PDF
                      </a>
                      <a
                        href={`/api/jobs/${activeJob.id}/html`}
                        target="_blank"
                        rel="noreferrer"
                        className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700"
                      >
                        Open HTML
                      </a>
                    </div>
                  </div>

                  {/* Embedded PDF iframe */}
                  <div className="w-full h-[650px] rounded-2xl overflow-hidden border border-slate-800 bg-slate-900 shadow-2xl">
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
                  <div className="flex items-center justify-between glass-panel p-4 rounded-xl border border-slate-800">
                    <div>
                      <h4 className="text-sm font-bold text-white">Custom Tailored Cover Letter</h4>
                      <p className="text-xs text-slate-400">
                        Personalized addressing {activeJob.company}'s specific challenges and values.
                      </p>
                    </div>
                    {tailoredOutput?.cover_letter && (
                      <button
                        onClick={() => handleCopyCoverLetter(tailoredOutput.cover_letter!)}
                        className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md transition-all"
                      >
                        {copiedCoverLetter ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copiedCoverLetter ? 'Copied!' : 'Copy to Clipboard'}</span>
                      </button>
                    )}
                  </div>

                  <div className="glass-panel p-6 rounded-2xl border border-slate-800 whitespace-pre-line font-serif text-sm text-slate-200 leading-relaxed bg-slate-900/60 shadow-lg">
                    {tailoredOutput?.cover_letter || (
                      <div className="text-center py-12 text-slate-400">
                        <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p>No cover letter generated yet.</p>
                        <button
                          onClick={() => onTailor(activeJob, true)}
                          className="mt-3 px-4 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-medium"
                        >
                          Generate Cover Letter
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* TAB CONTENT: ATS VALIDATION REPORT */}
              {activeTab === 'validation' && (
                <div className="space-y-4">
                  <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-3">
                    <h4 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" /> Automated ATS Inspection
                    </h4>
                    {tailoredOutput?.validation_report ? (
                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-slate-300">
                            Status:{' '}
                            <span
                              className={
                                tailoredOutput.validation_report.passed
                                  ? 'text-emerald-400'
                                  : 'text-amber-400'
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
                              className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center gap-2"
                            >
                              {chk.passed ? (
                                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                              ) : (
                                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                              )}
                              <span className="text-slate-300">{chk.name}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-400">Validation report not yet generated.</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-slate-500">
              <Briefcase className="w-12 h-12 mb-3 opacity-30 text-slate-400" />
              <p className="font-semibold text-slate-300">Select a job from the left panel</p>
              <p className="text-xs text-slate-500 mt-1">
                View role fit score, compensation, full job description, and tailor your resume.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
