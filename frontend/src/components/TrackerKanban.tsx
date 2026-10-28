import React from 'react'
import {
  ExternalLink,
  Trash2,
  FileText,
  Calendar,
  Building2,
  Clock,
  CheckCircle2,
} from 'lucide-react'
import { TrackerApplication } from '../types'

interface TrackerKanbanProps {
  applications: TrackerApplication[]
  onUpdateStatus: (jobId: string, newStatus: string, notes?: string) => void
  onDelete: (jobId: string) => void
  onSelectJobForReview: (jobId: string) => void
}

const STAGES = [
  { id: 'saved', title: 'Saved', color: 'border-slate-500', badge: 'bg-slate-800 text-slate-300' },
  { id: 'applied', title: 'Applied', color: 'border-blue-500', badge: 'bg-blue-500/15 text-blue-400' },
  { id: 'interviewing', title: 'Interviewing', color: 'border-purple-500', badge: 'bg-purple-500/15 text-purple-400' },
  { id: 'offer', title: 'Offer', color: 'border-emerald-500', badge: 'bg-emerald-500/15 text-emerald-400' },
  { id: 'rejected', title: 'Archived / Rejected', color: 'border-rose-500', badge: 'bg-rose-500/15 text-rose-400' },
]

export const TrackerKanban: React.FC<TrackerKanbanProps> = ({
  applications,
  onUpdateStatus,
  onDelete,
  onSelectJobForReview,
}) => {
  return (
    <div className="p-6 h-[calc(100vh-4rem)] overflow-x-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Application Pipeline</h2>
          <p className="text-xs text-slate-400">
            Track interview rounds, offers, and tailored job applications in real time.
          </p>
        </div>
        <div className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300">
          Total Applications: {applications.length}
        </div>
      </div>

      <div className="flex gap-4 min-w-[1100px] h-[calc(100%-4rem)] pb-4">
        {STAGES.map((stage) => {
          const stageApps = applications.filter((a) => {
            if (stage.id === 'applied' && a.status === 'ready_for_review') return true
            return a.status === stage.id
          })

          return (
            <div
              key={stage.id}
              className="flex-1 bg-slate-900/60 border border-slate-800 rounded-2xl flex flex-col overflow-hidden shadow-lg"
            >
              {/* Column Header */}
              <div className={`px-4 py-3 border-b border-slate-800 flex items-center justify-between bg-slate-900/80 border-t-2 ${stage.color}`}>
                <span className="font-semibold text-xs text-white uppercase tracking-wider">
                  {stage.title}
                </span>
                <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${stage.badge}`}>
                  {stageApps.length}
                </span>
              </div>

              {/* Column Cards */}
              <div className="flex-1 p-3 overflow-y-auto space-y-3">
                {stageApps.length === 0 ? (
                  <div className="text-center py-8 text-slate-600 text-xs">No jobs in this stage</div>
                ) : (
                  stageApps.map((app) => (
                    <div
                      key={app.job_id}
                      className="glass-card p-4 rounded-xl border border-slate-800/80 space-y-3 hover:border-slate-700 transition-all shadow-sm"
                    >
                      <div>
                        <h4 className="text-sm font-bold text-white line-clamp-1">{app.title}</h4>
                        <p className="text-xs text-blue-400 font-medium flex items-center gap-1 mt-0.5">
                          <Building2 className="w-3 h-3" />
                          {app.company}
                        </p>
                      </div>

                      {/* Status row */}
                      <div className="flex items-center justify-between text-[11px] text-slate-400">
                        {app.coverage_score ? (
                          <span className="flex items-center gap-1 text-emerald-400 font-medium">
                            <CheckCircle2 className="w-3 h-3" />
                            {Math.round(app.coverage_score * 100)}% match
                          </span>
                        ) : (
                          <span>Tracked</span>
                        )}
                        {app.updated_at && (
                          <span className="flex items-center gap-1 text-slate-500">
                            <Clock className="w-3 h-3" />
                            {new Date(app.updated_at).toLocaleDateString()}
                          </span>
                        )}
                      </div>

                      {/* Stage selector dropdown */}
                      <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between gap-2">
                        <select
                          value={app.status}
                          onChange={(e) => onUpdateStatus(app.job_id, e.target.value)}
                          className="bg-slate-800 border border-slate-700 text-[11px] text-slate-200 rounded-lg px-2 py-1 font-medium focus:outline-none cursor-pointer"
                        >
                          <option value="saved">Saved</option>
                          <option value="applied">Applied</option>
                          <option value="interviewing">Interviewing</option>
                          <option value="offer">Offer</option>
                          <option value="rejected">Archived</option>
                        </select>

                        <div className="flex items-center gap-1">
                          {app.application_url && (
                            <a
                              href={app.application_url}
                              target="_blank"
                              rel="noreferrer"
                              className="p-1 text-slate-400 hover:text-white"
                              title="Application Link"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                          )}
                          <button
                            onClick={() => onDelete(app.job_id)}
                            className="p-1 text-slate-500 hover:text-rose-400"
                            title="Remove from Pipeline"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
