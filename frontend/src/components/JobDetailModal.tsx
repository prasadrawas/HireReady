import React from 'react'
import {
  X,
  ExternalLink,
  Sparkles,
  MapPin,
  DollarSign,
  AlertTriangle,
  CheckCircle2,
  Bookmark,
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

  const matchPct = Math.round((job.score || 0.5) * 100)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="glass-panel w-full max-w-4xl rounded-2xl overflow-hidden shadow-2xl border border-slate-700/60 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-800 bg-slate-900/80 flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-500/15 text-blue-400 border border-blue-500/30">
                {matchPct}% Match
              </span>
              <span className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-800 text-slate-400 border border-slate-700 uppercase">
                {job.ats_source}
              </span>
              {job.remote && (
                <span className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                  Remote
                </span>
              )}
            </div>
            <h2 className="text-xl font-bold text-white mb-1">{job.title}</h2>
            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400">
              <span className="flex items-center gap-1 font-medium text-slate-300">
                <Building2 className="w-3.5 h-3.5 text-blue-400" />
                {job.company}
              </span>
              {job.location && (
                <span className="flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-slate-500" />
                  {job.location}
                </span>
              )}
              {job.posted_date && (
                <span className="flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5 text-slate-500" />
                  Posted: {job.posted_date}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => onTailor(job, true)}
              disabled={isTailoring}
              className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-blue-600/30 transition-all"
            >
              <Sparkles className="w-4 h-4 text-blue-200" />
              <span>{isTailoring ? 'Tailoring...' : 'Tailor Resume'}</span>
            </button>

            <a
              href={job.application_url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
              title="Open Official Job Board"
            >
              <ExternalLink className="w-4 h-4" />
            </a>

            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
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
            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
              <span className="text-xs font-medium text-slate-400 block mb-1 flex items-center gap-1.5">
                <DollarSign className="w-4 h-4 text-emerald-400" />
                Salary & Compensation
              </span>
              <p className="text-sm font-semibold text-white">
                {job.salary || 'Not explicitly listed in JD'}
              </p>
            </div>

            {/* Recommendation */}
            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
              <span className="text-xs font-medium text-slate-400 block mb-1 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-blue-400" />
                Scorer Recommendation
              </span>
              <p className="text-sm font-semibold text-white capitalize">
                {job.recommendation?.replace('_', ' ') || 'Consider Application'}
              </p>
            </div>

            {/* Red Flags */}
            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
              <span className="text-xs font-medium text-slate-400 block mb-1 flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Red Flag Detector
              </span>
              <p className="text-sm font-semibold text-white">
                {job.red_flag_count && job.red_flag_count > 0
                  ? `${job.red_flag_count} Potential Warning(s)`
                  : 'Clean Job Description'}
              </p>
            </div>
          </div>

          {/* Role Fit & Skill Gaps */}
          {(job.role_fit || (job.key_gaps && job.key_gaps.length > 0)) && (
            <div className="bg-slate-900/40 p-4 rounded-xl border border-slate-800 space-y-3">
              <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Gemini Role Fit Analysis
              </h4>
              {job.role_fit && (
                <p className="text-sm text-slate-300 leading-relaxed italic">"{job.role_fit}"</p>
              )}
              {job.key_gaps && job.key_gaps.length > 0 && (
                <div>
                  <span className="text-xs font-medium text-amber-400 block mb-1.5">
                    Identified Skill Gaps / Missing Keywords:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {job.key_gaps.map((gap, i) => (
                      <span
                        key={i}
                        className="text-xs bg-amber-500/10 text-amber-300 border border-amber-500/20 px-2 py-0.5 rounded-md"
                      >
                        {gap}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Red Flag Warnings List */}
          {job.red_flags && job.red_flags.length > 0 && (
            <div className="bg-amber-950/20 p-4 rounded-xl border border-amber-900/40">
              <h4 className="text-xs font-semibold text-amber-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4" /> Detected Red Flags
              </h4>
              <ul className="list-disc list-inside text-xs text-amber-200/90 space-y-1">
                {job.red_flags.map((flag, idx) => (
                  <li key={idx}>{flag}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Full Job Description */}
          <div>
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
              Job Description
            </h4>
            <div
              className="prose prose-invert max-w-none text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-5 rounded-xl border border-slate-800/80 max-h-[400px] overflow-y-auto"
              dangerouslySetInnerHTML={{
                __html: job.description_html || job.description_text || 'No description provided.',
              }}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Pipeline Stage:</span>
            <select
              value={job.tracker_status || 'none'}
              onChange={(e) => onTrack(job, e.target.value)}
              className="bg-slate-800 border border-slate-700 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
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
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
