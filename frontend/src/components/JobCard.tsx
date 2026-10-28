import React from 'react'
import {
  ExternalLink,
  Sparkles,
  MapPin,
  DollarSign,
  AlertTriangle,
  CheckCircle2,
  Bookmark,
  FileText,
} from 'lucide-react'
import { JobListing } from '../types'

interface JobCardProps {
  job: JobListing
  onSelect: (job: JobListing) => void
  onTailor: (job: JobListing) => void
  onTrack: (job: JobListing, status: string) => void
  isTailoring: boolean
}

export const JobCard: React.FC<JobCardProps> = ({
  job,
  onSelect,
  onTailor,
  onTrack,
  isTailoring,
}) => {
  const matchPct = Math.round((job.score || 0.5) * 100)

  const scoreBadgeColor =
    matchPct >= 70
      ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
      : matchPct >= 50
      ? 'bg-blue-500/15 text-blue-400 border-blue-500/30'
      : 'bg-amber-500/15 text-amber-400 border-amber-500/30'

  return (
    <div className="glass-card rounded-2xl p-5 flex flex-col justify-between transition-all duration-200 hover:-translate-y-1">
      <div>
        {/* Header Badges */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <span
              className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${scoreBadgeColor}`}
            >
              {matchPct}% Match
            </span>
            <span className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-800 text-slate-400 border border-slate-700 uppercase tracking-wider">
              {job.ats_source}
            </span>
          </div>

          {job.has_tailored_resume && (
            <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
              <CheckCircle2 className="w-3 h-3" />
              Tailored
            </span>
          )}
        </div>

        {/* Company & Title */}
        <h3
          onClick={() => onSelect(job)}
          className="text-base font-semibold text-white hover:text-blue-400 transition-colors cursor-pointer line-clamp-1 mb-1"
        >
          {job.title}
        </h3>
        <p className="text-xs font-medium text-slate-400 mb-3">{job.company}</p>

        {/* Tags / Metadata */}
        <div className="flex flex-wrap items-center gap-2 mb-4 text-xs text-slate-400">
          <span className="flex items-center gap-1 bg-slate-900/60 px-2 py-1 rounded-md border border-slate-800">
            <MapPin className="w-3 h-3 text-slate-500" />
            <span className="truncate max-w-[140px]">{job.location || 'Remote'}</span>
          </span>

          <span className="flex items-center gap-1 bg-slate-900/60 px-2 py-1 rounded-md border border-slate-800">
            <DollarSign className="w-3 h-3 text-emerald-500" />
            <span className="truncate max-w-[120px]">{job.salary || 'Not listed'}</span>
          </span>

          {job.red_flag_count && job.red_flag_count > 0 ? (
            <span className="flex items-center gap-1 bg-amber-500/10 text-amber-400 px-2 py-1 rounded-md border border-amber-500/20">
              <AlertTriangle className="w-3 h-3" />
              <span>{job.red_flag_count} Flags</span>
            </span>
          ) : (
            <span className="flex items-center gap-1 bg-slate-900/40 text-slate-500 px-2 py-1 rounded-md border border-slate-800/80">
              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
              <span>Clean JD</span>
            </span>
          )}
        </div>

        {/* Role Fit / Gaps Snippet */}
        {job.role_fit && (
          <p className="text-xs text-slate-400 line-clamp-2 bg-slate-900/40 p-2.5 rounded-lg border border-slate-800/60 mb-4 italic">
            "{job.role_fit}"
          </p>
        )}
      </div>

      {/* Card Actions */}
      <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => onSelect(job)}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
          >
            Details
          </button>

          <a
            href={job.application_url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 rounded-lg bg-slate-800/60 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
            title="Open Application Board"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>

          <button
            onClick={() => onTrack(job, job.tracker_status === 'saved' ? 'applied' : 'saved')}
            className={`p-1.5 rounded-lg border transition-colors ${
              job.tracker_status
                ? 'bg-blue-600/20 border-blue-500/40 text-blue-400'
                : 'bg-slate-800/60 border-slate-700 text-slate-400 hover:text-white'
            }`}
            title={job.tracker_status ? `Stage: ${job.tracker_status}` : 'Save to Pipeline'}
          >
            <Bookmark className="w-3.5 h-3.5" />
          </button>
        </div>

        <button
          onClick={() => onTailor(job)}
          disabled={isTailoring}
          className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800/50 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-blue-600/20 transition-all"
        >
          {isTailoring ? (
            <span className="animate-spin text-xs">⟳</span>
          ) : (
            <Sparkles className="w-3.5 h-3.5 text-blue-200" />
          )}
          <span>{job.has_tailored_resume ? 'Re-Tailor' : 'Tailor'}</span>
        </button>
      </div>
    </div>
  )
}
