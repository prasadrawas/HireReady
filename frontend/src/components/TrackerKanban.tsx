import React from 'react'
import {
  ExternalLink,
  Trash2,
  Building2,
  Clock,
  CheckCircle2,
  Layers,
  ArrowRight,
} from 'lucide-react'
import { TrackerApplication } from '../types'

interface TrackerKanbanProps {
  applications: TrackerApplication[]
  onUpdateStatus: (jobId: string, newStatus: string, notes?: string) => void
  onDelete: (jobId: string) => void
  onSelectJobForReview: (jobId: string) => void
}

const STAGES = [
  { id: 'saved', title: 'Saved Jobs', borderTop: 'border-t-slate-400', badge: 'bg-slate-100 text-slate-700 border border-slate-200' },
  { id: 'applied', title: 'Applied', borderTop: 'border-t-[#0a66c2]', badge: 'bg-blue-50 text-[#0a66c2] border border-blue-200' },
  { id: 'interviewing', title: 'Interviewing', borderTop: 'border-t-purple-600', badge: 'bg-purple-50 text-purple-700 border border-purple-200' },
  { id: 'offer', title: 'Job Offers', borderTop: 'border-t-[#057642]', badge: 'bg-emerald-50 text-[#057642] border border-emerald-200' },
  { id: 'rejected', title: 'Archived', borderTop: 'border-t-slate-300', badge: 'bg-slate-100 text-slate-500 border border-slate-200' },
]

export const TrackerKanban: React.FC<TrackerKanbanProps> = ({
  applications,
  onUpdateStatus,
  onDelete,
  onSelectJobForReview,
}) => {
  return (
    <div className="bg-[#f4f2ee] h-[calc(100vh-3.5rem)] overflow-y-auto p-4 sm:p-6 flex flex-col">
      <div className="max-w-7xl w-full mx-auto flex flex-col flex-1">
        {/* Header Bar */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 sm:p-5 mb-5 flex flex-wrap items-center justify-between gap-3 shadow-xs">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-[#edf3f8] text-[#0a66c2]">
                <Layers className="w-4 h-4" />
              </span>
              <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                My Job Applications Pipeline
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Organize interview stages, tailor follow-ups, and monitor status across all ATS boards.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold px-3 py-1.5 rounded-full bg-[#edf3f8] text-[#0a66c2] border border-[#d0e2f5]">
              {applications.length} Tracked Roles
            </span>
          </div>
        </div>

        {/* Kanban Board Columns */}
        <div className="flex gap-4 min-w-[1050px] flex-1 pb-4 overflow-x-auto">
          {STAGES.map((stage) => {
            const stageApps = applications.filter((a) => {
              if (stage.id === 'applied' && a.status === 'ready_for_review') return true
              return a.status === stage.id
            })

            return (
              <div
                key={stage.id}
                className="flex-1 bg-[#ebedf0]/70 rounded-xl border border-slate-200/80 flex flex-col overflow-hidden shadow-2xs"
              >
                {/* Column Header */}
                <div
                  className={`px-4 py-3 bg-white border-b border-slate-200 flex items-center justify-between border-t-4 ${stage.borderTop}`}
                >
                  <span className="font-bold text-xs text-slate-900 tracking-tight">
                    {stage.title}
                  </span>
                  <span className={`text-[11px] px-2 py-0.5 rounded-full font-bold ${stage.badge}`}>
                    {stageApps.length}
                  </span>
                </div>

                {/* Column Cards */}
                <div className="flex-1 p-3 overflow-y-auto space-y-3">
                  {stageApps.length === 0 ? (
                    <div className="text-center py-10 text-slate-400 text-xs">
                      No jobs in this stage
                    </div>
                  ) : (
                    stageApps.map((app) => (
                      <div
                        key={app.job_id}
                        className="bg-white p-4 rounded-xl border border-slate-200 space-y-3 hover:border-[#0a66c2] hover:shadow-sm transition-all shadow-2xs group"
                      >
                        <div
                          className="cursor-pointer"
                          onClick={() => onSelectJobForReview(app.job_id)}
                        >
                          <h4 className="text-sm font-semibold text-slate-900 group-hover:text-[#0a66c2] transition-colors line-clamp-1">
                            {app.title}
                          </h4>
                          <p className="text-xs text-slate-600 font-normal flex items-center gap-1.5 mt-0.5">
                            <Building2 className="w-3.5 h-3.5 text-slate-400" />
                            {app.company}
                          </p>
                        </div>

                        {/* Match & Date Line */}
                        <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-100">
                          {app.coverage_score ? (
                            <span className="flex items-center gap-1 text-[#057642] font-semibold bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                              <CheckCircle2 className="w-3 h-3" />
                              {Math.round(app.coverage_score * 100)}% Match
                            </span>
                          ) : (
                            <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-medium">
                              Tracked
                            </span>
                          )}

                          {app.updated_at && (
                            <span className="flex items-center gap-1 text-slate-400 text-[10px]">
                              <Clock className="w-3 h-3" />
                              {new Date(app.updated_at).toLocaleDateString()}
                            </span>
                          )}
                        </div>

                        {/* Stage Dropdown & Action Links */}
                        <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
                          <select
                            value={app.status}
                            onChange={(e) => onUpdateStatus(app.job_id, e.target.value)}
                            className="bg-[#edf3f8] hover:bg-[#e4ebf2] border border-transparent focus:border-[#0a66c2] text-xs font-semibold text-slate-700 rounded-full px-2.5 py-1 focus:outline-none cursor-pointer transition-colors"
                          >
                            <option value="saved">Saved</option>
                            <option value="applied">Applied</option>
                            <option value="interviewing">Interviewing</option>
                            <option value="offer">Offer</option>
                            <option value="rejected">Archived</option>
                          </select>

                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => onSelectJobForReview(app.job_id)}
                              className="p-1.5 text-slate-400 hover:text-[#0a66c2] rounded-full hover:bg-slate-100 transition-colors"
                              title="Review Job Details"
                            >
                              <ArrowRight className="w-3.5 h-3.5" />
                            </button>

                            {app.application_url && (
                              <a
                                href={app.application_url}
                                target="_blank"
                                rel="noreferrer"
                                className="p-1.5 text-slate-400 hover:text-[#0a66c2] rounded-full hover:bg-slate-100 transition-colors"
                                title="Open Job Application"
                              >
                                <ExternalLink className="w-3.5 h-3.5" />
                              </a>
                            )}

                            <button
                              onClick={() => onDelete(app.job_id)}
                              className="p-1.5 text-slate-400 hover:text-rose-600 rounded-full hover:bg-rose-50 transition-colors"
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
    </div>
  )
}
