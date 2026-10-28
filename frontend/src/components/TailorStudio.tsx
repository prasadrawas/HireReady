import React, { useState } from 'react'
import {
  FileText,
  Download,
  Copy,
  Check,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  Sparkles,
  Building2,
  ChevronRight,
  Flag,
  Info,
  ZoomIn,
  ZoomOut,
} from 'lucide-react'
import { JobListing, JobOutput } from '../types'

interface TailorStudioProps {
  jobs: JobListing[]
  selectedJob: JobListing | null
  onSelectJob: (job: JobListing) => void
  tailoredOutput: JobOutput | null
  onTailor: (job: JobListing, coverLetter: boolean) => Promise<void>
  isTailoring: boolean
  darkMode: boolean
}

type StudioTab = 'pdf' | 'cover_letter' | 'changes' | 'company' | 'ats'

const ZOOM_LEVELS = [75, 100, 125, 150] as const

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

export const TailorStudio: React.FC<TailorStudioProps> = ({
  jobs,
  selectedJob,
  onSelectJob,
  tailoredOutput,
  onTailor,
  isTailoring,
  darkMode,
}) => {
  const [activeTab, setActiveTab] = useState<StudioTab>('pdf')
  const [copiedCL, setCopiedCL] = useState(false)
  const [pdfZoom, setPdfZoom] = useState<number>(100)

  // Filter only jobs that have been tailored or all ranked jobs
  const tailoredJobs = jobs.filter((j) => j.has_tailored_resume)
  const currentJob = selectedJob || tailoredJobs[0] || jobs[0] || null

  const handleCopyCL = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedCL(true)
    setTimeout(() => setCopiedCL(false), 2000)
  }

  // Fallback company avatar color
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

  if (!currentJob) {
    return (
      <div className={`h-[calc(100vh-3.5rem)] flex items-center justify-center p-6 ${darkMode ? 'bg-[#1a1a2e]' : 'bg-[#f4f2ee]'}`}>
        <div className={`p-10 rounded-2xl border text-center max-w-md shadow-xs ${darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'}`}>
          <FileText className={`w-12 h-12 mx-auto mb-3 ${darkMode ? 'text-slate-600' : 'text-slate-300'}`} />
          <h3 className={`text-base font-bold ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>No jobs tailored yet</h3>
          <p className={`text-xs mt-1 leading-relaxed ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
            Scan your target ATS job boards and click "Tailor Resume" on any matching listing to create customized PDF resumes and cover letters.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={`flex h-[calc(100vh-3.5rem)] overflow-hidden ${darkMode ? 'bg-[#1a1a2e]' : 'bg-[#f4f2ee]'}`}>
      {/* Left Sidebar: Select Tailored Job */}
      <div className={`w-80 border-r overflow-y-auto p-4 space-y-2 shrink-0 shadow-xs flex flex-col ${
        darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'
      }`}>
        <div className="flex items-center justify-between mb-2 px-1">
          <h3 className={`text-xs font-bold uppercase tracking-wider ${darkMode ? 'text-slate-400' : 'text-slate-700'}`}>
            Tailored Roles
          </h3>
          <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full border ${
            darkMode ? 'bg-[#1e3a5f] text-[#0a66c2] border-[#2a4a6f]' : 'bg-[#edf3f8] text-[#0a66c2] border-[#d0e2f5]'
          }`}>
            {tailoredJobs.length} Ready
          </span>
        </div>

        <div className="flex-1 space-y-1.5 overflow-y-auto">
          {tailoredJobs.length === 0 ? (
            <div className={`p-4 rounded-xl border text-center ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-slate-50 border-slate-200'}`}>
              <p className={`text-xs leading-relaxed ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                No roles tailored yet. Go to the <span className="font-semibold text-[#0a66c2]">Jobs</span> tab and select "Tailor Resume" on any listing.
              </p>
            </div>
          ) : (
            tailoredJobs.map((job) => {
              const isSelected = currentJob.id === job.id
              const avatarColor = getAvatarColor(job.company)
              return (
                <div
                  key={job.id}
                  onClick={() => onSelectJob(job)}
                  className={`p-3 rounded-xl cursor-pointer transition-all flex items-center gap-3 border ${
                    isSelected
                      ? darkMode
                        ? 'bg-[#1e3a5f] border-[#0a66c2] shadow-2xs'
                        : 'bg-[#edf3f8] border-[#0a66c2] shadow-2xs'
                      : darkMode
                      ? 'bg-[#16213e] border-[#1e3a5f] hover:bg-[#1e3a5f] text-slate-300'
                      : 'bg-white border-slate-200 hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  <div
                    className={`w-9 h-9 rounded-lg ${avatarColor} flex items-center justify-center text-white font-bold text-xs shrink-0 shadow-xs`}
                  >
                    {job.company.substring(0, 2).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4
                      className={`text-xs font-bold truncate ${
                        isSelected ? 'text-[#0a66c2]' : darkMode ? 'text-slate-200' : 'text-slate-900'
                      }`}
                    >
                      {job.title}
                    </h4>
                    <p className={`text-[11px] truncate mt-0.5 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>{job.company}</p>
                  </div>
                  <ChevronRight
                    className={`w-4 h-4 shrink-0 ${
                      isSelected ? 'text-[#0a66c2]' : darkMode ? 'text-slate-600' : 'text-slate-300'
                    }`}
                  />
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* Main Studio Area */}
      <div className={`flex-1 flex flex-col overflow-hidden ${darkMode ? 'bg-[#1a1a2e]' : 'bg-[#f4f2ee]'}`}>
        {/* Studio Header */}
        <div className={`p-4 sm:p-5 border-b flex flex-wrap items-center justify-between gap-4 shrink-0 shadow-xs ${
          darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'
        }`}>
          <div className="flex items-center gap-3.5">
            <div
              className={`w-12 h-12 rounded-lg ${getAvatarColor(
                currentJob.company
              )} flex items-center justify-center text-white font-bold text-base shrink-0 shadow-xs`}
            >
              {currentJob.company.substring(0, 2).toUpperCase()}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className={`text-xs font-bold ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>{currentJob.company}</span>
                <span className={darkMode ? 'text-slate-600' : 'text-slate-300'}>&bull;</span>
                <span className={`text-[11px] uppercase font-semibold ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                  {currentJob.ats_source}
                </span>
                {currentJob.remote && (
                  <span className="text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.2 rounded-full font-bold">
                    Remote
                  </span>
                )}
              </div>
              <h2 className={`text-xl font-bold tracking-tight mt-0.5 ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>
                {currentJob.title}
              </h2>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => onTailor(currentJob, true)}
              disabled={isTailoring}
              className="px-4 py-2 rounded-full bg-purple-700 hover:bg-purple-800 text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer disabled:opacity-50"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{isTailoring ? 'Regenerating...' : 'Regenerate Tailored Assets'}</span>
            </button>

            {currentJob.has_tailored_resume && (
              <a
                href={`/api/jobs/${currentJob.id}/pdf`}
                download={`Resume_${currentJob.company}_${currentJob.title}.pdf`}
                className="px-4 py-2 rounded-full bg-[#057642] hover:bg-[#046237] text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" /> Download PDF
              </a>
            )}

            <a
              href={currentJob.application_url}
              target="_blank"
              rel="noreferrer"
              className={`p-2 rounded-full border transition-colors ${
                darkMode ? 'border-[#1e3a5f] hover:bg-[#1e3a5f] text-slate-400' : 'border-slate-300 hover:bg-slate-100 text-slate-600'
              }`}
              title="Open Official Job Board"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        </div>

        {/* Studio Subtabs */}
        <div className={`px-6 py-2.5 border-b flex items-center gap-2 shrink-0 ${
          darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'
        }`}>
          {([
            { id: 'pdf' as StudioTab, label: 'PDF Resume Preview' },
            { id: 'cover_letter' as StudioTab, label: 'Cover Letter' },
            { id: 'changes' as StudioTab, label: 'Change Summary & Diff' },
            { id: 'company' as StudioTab, label: 'Company Brief' },
            { id: 'ats' as StudioTab, label: 'ATS Verification' },
          ]).map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
                activeTab === tab.id
                  ? 'bg-[#01754f] text-white shadow-xs'
                  : darkMode
                  ? 'bg-[#16213e] hover:bg-[#1e3a5f] text-slate-300 border border-[#1e3a5f]'
                  : 'bg-white hover:bg-slate-100 text-slate-700 border border-slate-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab View Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          {activeTab === 'pdf' && (
            <div className="max-w-5xl mx-auto w-full space-y-3">
              {/* Zoom Controls */}
              <div className={`flex items-center gap-2 p-2 rounded-lg ${darkMode ? 'bg-[#16213e]' : 'bg-white'} border ${darkMode ? 'border-[#1e3a5f]' : 'border-slate-200'}`}>
                <ZoomOut className={`w-4 h-4 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`} />
                {ZOOM_LEVELS.map((level) => (
                  <button
                    key={level}
                    onClick={() => setPdfZoom(level)}
                    className={`px-2.5 py-1 rounded-full text-xs font-semibold cursor-pointer transition-all ${
                      pdfZoom === level
                        ? 'bg-[#0a66c2] text-white'
                        : darkMode
                        ? 'text-slate-300 hover:bg-[#1e3a5f]'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    {level}%
                  </button>
                ))}
                <ZoomIn className={`w-4 h-4 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`} />
              </div>

              <div
                className={`rounded-xl overflow-auto border shadow-xs ${darkMode ? 'border-[#2a4a6f] bg-[#1e3a5f]' : 'border-slate-200 bg-white'}`}
                style={{ height: '700px' }}
              >
                <iframe
                  src={`/api/jobs/${currentJob.id}/pdf`}
                  className="h-full"
                  style={{ width: `${pdfZoom}%`, minWidth: '100%', transformOrigin: 'top left', transform: `scale(${pdfZoom / 100})` }}
                  title="Tailored Resume Preview"
                />
              </div>
            </div>
          )}

          {activeTab === 'cover_letter' && (
            <div className="max-w-3xl mx-auto space-y-4">
              <div className={`p-4 rounded-xl border flex items-center justify-between shadow-2xs ${
                darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'
              }`}>
                <div>
                  <h4 className={`text-sm font-bold ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>Targeted Cover Letter</h4>
                  <p className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                    Drafted specifically for {currentJob.company} highlighting your key technical strengths.
                  </p>
                </div>
                {coverLetterText && (
                  <button
                    onClick={() => handleCopyCL(coverLetterText)}
                    className="px-4 py-2 rounded-full bg-[#0a66c2] hover:bg-[#004182] text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
                  >
                    {copiedCL ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedCL ? 'Copied!' : 'Copy to Clipboard'}</span>
                  </button>
                )}
              </div>
              <div className={`p-6 sm:p-8 rounded-xl border whitespace-pre-line text-sm leading-relaxed font-serif shadow-xs ${
                darkMode ? 'bg-[#16213e] border-[#1e3a5f] text-slate-200' : 'bg-white border-slate-200 text-slate-800'
              }`}>
                {coverLetterText || (
                  <div className={`text-center py-12 font-sans ${darkMode ? 'text-slate-500' : 'text-slate-400'}`}>
                    <FileText className="w-8 h-8 mx-auto mb-2 opacity-40" />
                    <p>No cover letter generated yet.</p>
                    <button
                      onClick={() => onTailor(currentJob, true)}
                      className="mt-3 px-4 py-1.5 rounded-full bg-[#0a66c2] text-white text-xs font-semibold cursor-pointer"
                    >
                      Generate Cover Letter
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'changes' && (
            <div className="max-w-4xl mx-auto space-y-4">
              <div className={`p-4 rounded-xl border shadow-2xs ${darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'}`}>
                <h4 className={`text-sm font-bold ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>Resume Tailoring Audit Trail</h4>
                <p className={`text-xs mt-0.5 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                  Detailed inspection of modifications made to align with {currentJob.company}'s requirements.
                </p>
              </div>

              {tailoredOutput?.change_summary ? (
                (() => {
                  const { removed, added, keywords } = parseDiffFromChangeSummary(tailoredOutput.change_summary || '')
                  return (
                    <div className="space-y-4">
                      {/* Keywords */}
                      {keywords.length > 0 && (
                        <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'}`}>
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
                          <div className={`border-b ${darkMode ? 'border-[#2a4a6f]' : 'border-slate-200'}`}>
                            <div className="px-4 py-2 bg-red-50 text-xs font-bold text-red-700 border-b border-red-200">Removed / Replaced</div>
                            <div className={`p-4 space-y-1 ${darkMode ? 'bg-[#16213e]' : ''}`}>
                              {removed.map((line, i) => (
                                <div key={i} className="diff-remove text-xs py-1 px-2 rounded">{line}</div>
                              ))}
                            </div>
                          </div>
                        )}
                        {added.length > 0 && (
                          <div>
                            <div className="px-4 py-2 bg-green-50 text-xs font-bold text-green-700 border-b border-green-200">Added / Updated</div>
                            <div className={`p-4 space-y-1 ${darkMode ? 'bg-[#16213e]' : ''}`}>
                              {added.map((line, i) => (
                                <div key={i} className="diff-add text-xs py-1 px-2 rounded">{line}</div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Raw Summary */}
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
                })()
              ) : (
                <div className={`p-6 rounded-xl border text-xs font-mono whitespace-pre-wrap leading-relaxed shadow-xs ${
                  darkMode ? 'bg-[#16213e] border-[#1e3a5f] text-slate-300' : 'bg-white border-slate-200 text-slate-800'
                }`}>
                  No change summary available.
                </div>
              )}
            </div>
          )}

          {/* Company Brief Tab */}
          {activeTab === 'company' && (
            <div className="max-w-3xl mx-auto space-y-4">
              <div className={`p-4 rounded-xl border shadow-2xs ${darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'}`}>
                <h4 className={`text-sm font-bold ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>Company Research Brief</h4>
                <p className={`text-xs mt-0.5 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                  Automated intelligence gathered about {currentJob.company}.
                </p>
              </div>

              {tailoredOutput?.company_brief ? (
                <div className="space-y-4">
                  {/* Company Header */}
                  <div className={`p-5 rounded-xl border ${darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'}`}>
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
                    <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'}`}>
                      <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Known For</h5>
                      <p className={`text-sm ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>{tailoredOutput.company_brief.known_for}</p>
                    </div>
                    <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'}`}>
                      <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Funding</h5>
                      <p className={`text-sm ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>{tailoredOutput.company_brief.funding_status}</p>
                    </div>
                    <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'}`}>
                      <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Glassdoor</h5>
                      <p className={`text-sm ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>{tailoredOutput.company_brief.glassdoor_sentiment}</p>
                    </div>
                    <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'}`}>
                      <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Verdict</h5>
                      <p className={`text-sm font-semibold ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>{tailoredOutput.company_brief.verdict}</p>
                    </div>
                  </div>

                  {/* Tech Stack */}
                  {tailoredOutput.company_brief.tech_stack_signals.length > 0 && (
                    <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'}`}>
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

                  {/* Culture */}
                  {tailoredOutput.company_brief.culture_signals.length > 0 && (
                    <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'}`}>
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
                <div className={`p-8 rounded-xl border text-center ${darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-slate-50 border-slate-200'}`}>
                  <Building2 className={`w-8 h-8 mx-auto mb-2 ${darkMode ? 'text-slate-600' : 'text-slate-300'}`} />
                  <p className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                    Company brief will appear after tailoring.
                  </p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'ats' && (
            <div className="max-w-3xl mx-auto space-y-4">
              <div className={`p-4 rounded-xl border shadow-2xs ${darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'}`}>
                <h4 className={`text-sm font-bold uppercase tracking-wider flex items-center gap-2 ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>
                  <ShieldCheck className="w-4 h-4 text-[#057642]" /> 9 Automated ATS Verification Checks
                </h4>
                <p className={`text-xs mt-0.5 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                  Ensures standard fonts, contact completeness, keyword density, and strict 1-page fit.
                </p>
              </div>

              {tailoredOutput?.validation_report?.checks ? (
                <div className="space-y-2">
                  {tailoredOutput.validation_report.checks.map((chk: any, idx: number) => (
                    <div
                      key={idx}
                      className={`p-3.5 rounded-xl border flex items-center justify-between text-xs shadow-2xs ${
                        darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        {chk.passed ? (
                          <CheckCircle2 className="w-4 h-4 text-[#057642]" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-amber-600" />
                        )}
                        <span className={`font-medium ${darkMode ? 'text-slate-200' : 'text-slate-900'}`}>{chk.name}</span>
                      </div>
                      <span
                        className={`font-bold px-2 py-0.5 rounded-full ${
                          chk.passed
                            ? 'bg-emerald-50 text-[#057642] border border-emerald-200'
                            : 'bg-amber-50 text-amber-700 border border-amber-200'
                        }`}
                      >
                        {chk.passed ? 'PASSED' : 'FLAGGED'}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className={`p-8 rounded-xl border text-center text-xs ${
                  darkMode ? 'bg-[#16213e] border-[#1e3a5f] text-slate-400' : 'bg-white border-slate-200 text-slate-500'
                }`}>
                  No ATS validation report available yet.
                </div>
              )}

              {/* Red Flags Section in ATS Tab */}
              {tailoredOutput?.red_flags && tailoredOutput.red_flags.flags.length > 0 && (
                <div className="space-y-3 mt-6">
                  <div className={`p-4 rounded-xl border flex items-center justify-between ${getVerdictColor(tailoredOutput.red_flags.verdict)}`}>
                    <div className="flex items-center gap-3">
                      <Flag className="w-5 h-5" />
                      <div>
                        <p className="text-sm font-bold">Red Flags: {tailoredOutput.red_flags.verdict.replace(/_/g, ' ')}</p>
                        <p className="text-xs mt-0.5">{tailoredOutput.red_flags.total} flags ({tailoredOutput.red_flags.critical} critical)</p>
                      </div>
                    </div>
                  </div>

                  {tailoredOutput.red_flags.flags.map((flag, idx) => (
                    <div key={idx} className={`p-3.5 rounded-xl border ${getSeverityColor(flag.severity)}`}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider">{flag.category}</span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getSeverityColor(flag.severity)}`}>
                          {flag.severity.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-xs font-semibold">{flag.signal}</p>
                      <p className="text-[11px] opacity-80 mt-0.5">{flag.evidence}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
