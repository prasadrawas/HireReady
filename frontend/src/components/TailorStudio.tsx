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

  if (!currentJob) {
    return (
      <div className="p-12 text-center text-slate-500">
        <FileText className="w-12 h-12 mx-auto mb-3 opacity-30 text-slate-400" />
        <h3 className="text-base font-semibold text-white">No jobs tailored yet</h3>
        <p className="text-xs text-slate-400 mt-1">
          Scan ATS boards and click "Tailor Resume" on any matching role to generate tailored assets.
        </p>
      </div>
    )
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden">
      {/* Left Sidebar: Select Tailored Job */}
      <div className="w-72 border-r border-slate-800 bg-slate-950/80 overflow-y-auto p-4 space-y-2 shrink-0">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 px-2">
          Tailored Jobs ({tailoredJobs.length})
        </h3>
        {tailoredJobs.length === 0 ? (
          <p className="text-xs text-slate-500 px-2 py-4 italic">
            None tailored yet. Select any role from the Jobs tab to tailor.
          </p>
        ) : (
          tailoredJobs.map((job) => {
            const isSelected = currentJob.id === job.id
            return (
              <div
                key={job.id}
                onClick={() => onSelectJob(job)}
                className={`p-3 rounded-xl cursor-pointer transition-all border ${
                  isSelected
                    ? 'bg-blue-600/15 border-blue-500/40 text-white'
                    : 'bg-slate-900/60 border-slate-800 text-slate-300 hover:bg-slate-800/80'
                }`}
              >
                <h4 className="text-xs font-bold truncate">{job.title}</h4>
                <p className="text-[11px] text-slate-400 mt-0.5">{job.company}</p>
              </div>
            )
          })
        )}
      </div>

      {/* Main Studio Area */}
      <div className="flex-1 flex flex-col overflow-hidden bg-slate-950">
        {/* Studio Header */}
        <div className="glass-panel p-5 border-b border-slate-800 flex items-center justify-between gap-4 shrink-0">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-bold text-blue-400">{currentJob.company}</span>
              <span className="text-slate-500">&bull;</span>
              <span className="text-xs text-slate-400 uppercase font-semibold">
                {currentJob.ats_source}
              </span>
            </div>
            <h2 className="text-lg font-bold text-white">{currentJob.title}</h2>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => onTailor(currentJob, true)}
              disabled={isTailoring}
              className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold flex items-center gap-2 shadow-md shadow-purple-600/30 transition-all disabled:opacity-50"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{isTailoring ? 'Regenerating...' : 'Regenerate Tailored Assets'}</span>
            </button>

            {currentJob.has_tailored_resume && (
              <a
                href={`/api/jobs/${currentJob.id}/pdf`}
                download={`Resume_${currentJob.company}_${currentJob.title}.pdf`}
                className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md transition-all"
              >
                <Download className="w-3.5 h-3.5" /> Download PDF
              </a>
            )}

            <a
              href={currentJob.application_url}
              target="_blank"
              rel="noreferrer"
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white"
              title="Open Official Job Board"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        </div>

        {/* Studio Subtabs */}
        <div className="px-6 py-2.5 bg-slate-900/60 border-b border-slate-800/80 flex items-center gap-2 shrink-0">
          <button
            onClick={() => setActiveTab('pdf')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'pdf' ? 'bg-slate-800 text-emerald-400 shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            PDF Resume Preview
          </button>
          <button
            onClick={() => setActiveTab('cover_letter')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'cover_letter' ? 'bg-slate-800 text-purple-400 shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Cover Letter
          </button>
          <button
            onClick={() => setActiveTab('changes')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'changes' ? 'bg-slate-800 text-blue-400 shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Change Summary & Diff
          </button>
          <button
            onClick={() => setActiveTab('ats')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'ats' ? 'bg-slate-800 text-amber-400 shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            ATS Inspection
          </button>
        </div>

        {/* Tab View Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'pdf' && (
            <div className="w-full h-full min-h-[700px] rounded-2xl overflow-hidden border border-slate-800 bg-slate-900 shadow-2xl">
              <iframe
                src={`/api/jobs/${currentJob.id}/pdf`}
                className="w-full h-full"
                title="Tailored Resume Preview"
              />
            </div>
          )}

          {activeTab === 'cover_letter' && (
            <div className="max-w-3xl mx-auto space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Targeted Cover Letter
                </span>
                {tailoredOutput?.cover_letter && (
                  <button
                    onClick={() => handleCopyCL(tailoredOutput.cover_letter!)}
                    className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md"
                  >
                    {copiedCL ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedCL ? 'Copied' : 'Copy Text'}</span>
                  </button>
                )}
              </div>
              <div className="glass-panel p-6 rounded-2xl border border-slate-800 whitespace-pre-line text-sm text-slate-200 leading-relaxed font-serif shadow-lg">
                {tailoredOutput?.cover_letter || 'No cover letter generated yet.'}
              </div>
            </div>
          )}

          {activeTab === 'changes' && (
            <div className="max-w-4xl mx-auto space-y-4">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                Tailored Resume Diff & Audit Trail
              </span>
              <div className="glass-panel p-6 rounded-2xl border border-slate-800 text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed max-h-[600px] overflow-y-auto">
                {tailoredOutput?.change_summary || 'No change summary available.'}
              </div>
            </div>
          )}

          {activeTab === 'ats' && (
            <div className="max-w-3xl mx-auto space-y-4">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                9 Automated ATS Verification Checks
              </span>
              {tailoredOutput?.validation_report?.checks ? (
                <div className="space-y-2">
                  {tailoredOutput.validation_report.checks.map((chk: any, idx: number) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center gap-2.5">
                        {chk.passed ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-amber-400" />
                        )}
                        <span className="text-white font-medium">{chk.name}</span>
                      </div>
                      <span
                        className={`font-semibold ${
                          chk.passed ? 'text-emerald-400' : 'text-amber-400'
                        }`}
                      >
                        {chk.passed ? 'PASSED' : 'FLAGGED'}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500">No ATS validation report available.</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
