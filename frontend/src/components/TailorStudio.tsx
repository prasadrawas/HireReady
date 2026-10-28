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
} from 'lucide-react'
import { JobListing, JobOutput } from '../types'

interface TailorStudioProps {
  jobs: JobListing[]
  selectedJob: JobListing | null
  onSelectJob: (job: JobListing) => void
  tailoredOutput: JobOutput | null
  onTailor: (job: JobListing, coverLetter: boolean) => Promise<void>
  isTailoring: boolean
}

export const TailorStudio: React.FC<TailorStudioProps> = ({
  jobs,
  selectedJob,
  onSelectJob,
  tailoredOutput,
  onTailor,
  isTailoring,
}) => {
  const [activeTab, setActiveTab] = useState<'pdf' | 'cover_letter' | 'changes' | 'ats'>('pdf')
  const [copiedCL, setCopiedCL] = useState(false)

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

  if (!currentJob) {
    return (
      <div className="bg-[#f4f2ee] h-[calc(100vh-3.5rem)] flex items-center justify-center p-6">
        <div className="bg-white p-10 rounded-2xl border border-slate-200 text-center max-w-md shadow-xs">
          <FileText className="w-12 h-12 mx-auto mb-3 text-slate-300" />
          <h3 className="text-base font-bold text-slate-900">No jobs tailored yet</h3>
          <p className="text-xs text-slate-500 mt-1 leading-relaxed">
            Scan your target ATS job boards and click "Tailor Resume" on any matching listing to create customized PDF resumes and cover letters.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden bg-[#f4f2ee]">
      {/* Left Sidebar: Select Tailored Job */}
      <div className="w-80 border-r border-slate-200 bg-white overflow-y-auto p-4 space-y-2 shrink-0 shadow-xs flex flex-col">
        <div className="flex items-center justify-between mb-2 px-1">
          <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
            Tailored Roles
          </h3>
          <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-[#edf3f8] text-[#0a66c2] border border-[#d0e2f5]">
            {tailoredJobs.length} Ready
          </span>
        </div>

        <div className="flex-1 space-y-1.5 overflow-y-auto">
          {tailoredJobs.length === 0 ? (
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-center">
              <p className="text-xs text-slate-500 leading-relaxed">
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
                      ? 'bg-[#edf3f8] border-[#0a66c2] shadow-2xs'
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
                        isSelected ? 'text-[#0a66c2]' : 'text-slate-900'
                      }`}
                    >
                      {job.title}
                    </h4>
                    <p className="text-[11px] text-slate-500 truncate mt-0.5">{job.company}</p>
                  </div>
                  <ChevronRight
                    className={`w-4 h-4 shrink-0 ${
                      isSelected ? 'text-[#0a66c2]' : 'text-slate-300'
                    }`}
                  />
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* Main Studio Area */}
      <div className="flex-1 flex flex-col overflow-hidden bg-[#f4f2ee]">
        {/* Studio Header */}
        <div className="bg-white p-4 sm:p-5 border-b border-slate-200 flex flex-wrap items-center justify-between gap-4 shrink-0 shadow-xs">
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
                <span className="text-xs font-bold text-slate-700">{currentJob.company}</span>
                <span className="text-slate-300">&bull;</span>
                <span className="text-[11px] text-slate-500 uppercase font-semibold">
                  {currentJob.ats_source}
                </span>
                {currentJob.remote && (
                  <span className="text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.2 rounded-full font-bold">
                    Remote
                  </span>
                )}
              </div>
              <h2 className="text-xl font-bold text-slate-900 tracking-tight mt-0.5">
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
              className="p-2 rounded-full border border-slate-300 hover:bg-slate-100 text-slate-600 transition-colors"
              title="Open Official Job Board"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        </div>

        {/* Studio Subtabs */}
        <div className="px-6 py-2.5 bg-white border-b border-slate-200 flex items-center gap-2 shrink-0">
          <button
            onClick={() => setActiveTab('pdf')}
            className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'pdf'
                ? 'bg-[#01754f] text-white shadow-xs'
                : 'bg-white hover:bg-slate-100 text-slate-700 border border-slate-300'
            }`}
          >
            PDF Resume Preview
          </button>
          <button
            onClick={() => setActiveTab('cover_letter')}
            className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'cover_letter'
                ? 'bg-[#01754f] text-white shadow-xs'
                : 'bg-white hover:bg-slate-100 text-slate-700 border border-slate-300'
            }`}
          >
            Cover Letter
          </button>
          <button
            onClick={() => setActiveTab('changes')}
            className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'changes'
                ? 'bg-[#01754f] text-white shadow-xs'
                : 'bg-white hover:bg-slate-100 text-slate-700 border border-slate-300'
            }`}
          >
            Change Summary & Diff
          </button>
          <button
            onClick={() => setActiveTab('ats')}
            className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'ats'
                ? 'bg-[#01754f] text-white shadow-xs'
                : 'bg-white hover:bg-slate-100 text-slate-700 border border-slate-300'
            }`}
          >
            ATS Verification Checks
          </button>
        </div>

        {/* Tab View Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          {activeTab === 'pdf' && (
            <div className="max-w-5xl mx-auto w-full h-full min-h-[700px] rounded-xl overflow-hidden border border-slate-200 bg-white shadow-xs">
              <iframe
                src={`/api/jobs/${currentJob.id}/pdf`}
                className="w-full h-full"
                title="Tailored Resume Preview"
              />
            </div>
          )}

          {activeTab === 'cover_letter' && (
            <div className="max-w-3xl mx-auto space-y-4">
              <div className="bg-white p-4 rounded-xl border border-slate-200 flex items-center justify-between shadow-2xs">
                <div>
                  <h4 className="text-sm font-bold text-slate-900">Targeted Cover Letter</h4>
                  <p className="text-xs text-slate-500">
                    Drafted specifically for {currentJob.company} highlighting your key technical strengths.
                  </p>
                </div>
                {tailoredOutput?.cover_letter && (
                  <button
                    onClick={() => handleCopyCL(tailoredOutput.cover_letter!)}
                    className="px-4 py-2 rounded-full bg-[#0a66c2] hover:bg-[#004182] text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
                  >
                    {copiedCL ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedCL ? 'Copied!' : 'Copy to Clipboard'}</span>
                  </button>
                )}
              </div>
              <div className="bg-white p-6 sm:p-8 rounded-xl border border-slate-200 whitespace-pre-line text-sm text-slate-800 leading-relaxed font-serif shadow-xs">
                {tailoredOutput?.cover_letter || (
                  <div className="text-center py-12 text-slate-400 font-sans">
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
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
                <h4 className="text-sm font-bold text-slate-900">Resume Tailoring Audit Trail</h4>
                <p className="text-xs text-slate-500 mt-0.5">
                  Detailed inspection of modifications made to align with {currentJob.company}'s requirements.
                </p>
              </div>
              <div className="bg-white p-6 rounded-xl border border-slate-200 text-xs text-slate-800 font-mono whitespace-pre-wrap leading-relaxed max-h-[600px] overflow-y-auto shadow-xs">
                {tailoredOutput?.change_summary || 'No change summary available.'}
              </div>
            </div>
          )}

          {activeTab === 'ats' && (
            <div className="max-w-3xl mx-auto space-y-4">
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
                <h4 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-[#057642]" /> 9 Automated ATS Verification Checks
                </h4>
                <p className="text-xs text-slate-500 mt-0.5">
                  Ensures standard fonts, contact completeness, keyword density, and strict 1-page fit.
                </p>
              </div>

              {tailoredOutput?.validation_report?.checks ? (
                <div className="space-y-2">
                  {tailoredOutput.validation_report.checks.map((chk: any, idx: number) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-xl bg-white border border-slate-200 flex items-center justify-between text-xs shadow-2xs"
                    >
                      <div className="flex items-center gap-2.5">
                        {chk.passed ? (
                          <CheckCircle2 className="w-4 h-4 text-[#057642]" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-amber-600" />
                        )}
                        <span className="text-slate-900 font-medium">{chk.name}</span>
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
                <div className="bg-white p-8 rounded-xl border border-slate-200 text-center text-slate-500 text-xs">
                  No ATS validation report available yet.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
