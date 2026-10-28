import React from 'react'
import {
  X,
  ExternalLink,
  Sparkles,
  MapPin,
  DollarSign,
  AlertTriangle,
  CheckCircle2,
  Building2,
  Calendar,
} from 'lucide-react'
import { JobListing } from '../types'

interface JobDetailModalProps {
  job: JobListing | null
  onClose: () => void
  onTailor: (job: JobListing, coverLetter: boolean) => void
  onTrack: (job: JobListing, status: string) => void
  isTailoring: boolean
}

export const JobDetailModal: React.FC<JobDetailModalProps> = ({
  job,
  onClose,
  onTailor,
  onTrack,
  isTailoring,
}) => {
  if (!job) return null

  const parseAndFormatJD = (rawHtml?: string, rawText?: string): string => {
    if (!rawHtml && !rawText) return '<p class="text-slate-400">No description provided.</p>'

    let str = rawHtml || rawText || ''
    if (str.includes('&lt;') || str.includes('&gt;') || str.includes('&quot;') || str.includes('&amp;')) {
      const parser = new DOMParser()
      const doc = parser.parseFromString(str, 'text/html')
      str = doc.body.innerHTML || doc.documentElement.textContent || str
      if (str.includes('&lt;') && str.includes('&gt;')) {
        const doc2 = parser.parseFromString(str, 'text/html')
        str = doc2.body.innerHTML || str
      }
    }
    str = str.replace(/style="[^"]*"/gi, '')
    str = str.replace(/style='[^']*'/gi, '')
    return str
  }

  const matchPct = Math.round((job.score || 0.5) * 100)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white w-full max-w-4xl rounded-2xl overflow-hidden shadow-2xl border border-slate-200 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-200 bg-white flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#edf3f8] text-[#0a66c2] border border-[#d0e2f5]">
                {matchPct}% Match
              </span>
              <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 uppercase">
                {job.ats_source}
              </span>
              {job.remote && (
                <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-50 text-[#057642] border border-emerald-200">
                  Remote
                </span>
              )}
            </div>
            <h2 className="text-xl font-bold text-slate-900 mb-1">{job.title}</h2>
            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
              <span className="flex items-center gap-1 font-semibold text-slate-800">
                <Building2 className="w-3.5 h-3.5 text-slate-500" />
                {job.company}
              </span>
              {job.location && (
                <span className="flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-slate-400" />
                  {job.location}
                </span>
              )}
              {job.posted_date && (
                <span className="flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5 text-slate-400" />
                  Posted: {job.posted_date}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => onTailor(job, false)}
              disabled={isTailoring}
              className="px-5 py-2 rounded-full bg-[#0a66c2] hover:bg-[#004182] text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer disabled:opacity-50"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{isTailoring ? 'Tailoring...' : 'Tailor Resume'}</span>
            </button>

            <a
              href={job.application_url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-full border border-slate-300 hover:bg-slate-100 text-slate-600 transition-colors"
              title="Open Official Job Board"
            >
              <ExternalLink className="w-4 h-4" />
            </a>

            <button
              onClick={onClose}
              className="p-2 rounded-full text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Key Insights Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Compensation */}
            <div className="bg-[#f8fafc] p-4 rounded-xl border border-slate-200">
              <span className="text-xs font-semibold text-slate-500 block mb-1 flex items-center gap-1.5">
                <DollarSign className="w-4 h-4 text-[#057642]" />
                Salary & Compensation
              </span>
              <p className="text-sm font-bold text-slate-900">
                {job.salary || 'Not explicitly listed in JD'}
              </p>
            </div>

            {/* Recommendation */}
            <div className="bg-[#f8fafc] p-4 rounded-xl border border-slate-200">
              <span className="text-xs font-semibold text-slate-500 block mb-1 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-[#0a66c2]" />
                Scorer Recommendation
              </span>
              <p className="text-sm font-bold text-slate-900 capitalize">
                {job.recommendation?.replace('_', ' ') || 'Consider Application'}
              </p>
            </div>

            {/* Red Flags */}
            <div className="bg-[#f8fafc] p-4 rounded-xl border border-slate-200">
              <span className="text-xs font-semibold text-slate-500 block mb-1 flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                Red Flag Detector
              </span>
              <p className="text-sm font-bold text-slate-900">
                {job.red_flag_count && job.red_flag_count > 0
                  ? `${job.red_flag_count} Potential Warning(s)`
                  : 'Clean Job Description'}
              </p>
            </div>
          </div>

          {/* Role Fit & Skill Gaps */}
          {(job.role_fit || (job.key_gaps && job.key_gaps.length > 0)) && (
            <div className="bg-[#fffbf2] border border-[#f5dfb8] p-4 rounded-xl space-y-3">
              <h4 className="text-xs font-bold text-[#b27800] uppercase tracking-wider">
                Role Fit & Alignment
              </h4>
              {job.role_fit && (
                <p className="text-sm text-slate-800 leading-relaxed italic">"{job.role_fit}"</p>
              )}
              {job.key_gaps && job.key_gaps.length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-amber-900 block mb-1.5">
                    Identified Skill Gaps / Missing Keywords:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {job.key_gaps.map((gap, i) => (
                      <span
                        key={i}
                        className="text-xs bg-amber-100 text-amber-900 border border-amber-300 px-2.5 py-0.5 rounded-full font-medium"
                      >
                        + {gap}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Red Flag Warnings List */}
          {job.red_flags && job.red_flags.length > 0 && (
            <div className="bg-amber-50 p-4 rounded-xl border border-amber-200">
              <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-600" /> Detected Red Flags
              </h4>
              <ul className="list-disc list-inside text-xs text-amber-900 space-y-1">
                {job.red_flags.map((flag, idx) => (
                  <li key={idx}>{flag}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Full Job Description */}
          <div>
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">
              Job Description
            </h4>
            <div
              className="jd-content bg-white p-6 rounded-xl border border-slate-200 max-h-[400px] overflow-y-auto"
              dangerouslySetInnerHTML={{
                __html: parseAndFormatJD(job.description_html, job.description_text),
              }}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 bg-white flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-slate-600">Pipeline Stage:</span>
            <select
              value={job.tracker_status || 'none'}
              onChange={(e) => onTrack(job, e.target.value)}
              className="bg-[#edf3f8] border border-slate-200 text-xs text-slate-800 font-semibold rounded-full px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#0a66c2] cursor-pointer"
            >
              <option value="none">Not in Pipeline</option>
              <option value="saved">Saved</option>
              <option value="applied">Applied</option>
              <option value="interviewing">Interviewing</option>
              <option value="offer">Offer</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>

          <button
            onClick={onClose}
            className="px-5 py-2 rounded-full border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-semibold transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
