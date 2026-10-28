import React, { useState } from 'react'
import {
  ExternalLink,
  Trash2,
  Building2,
  Clock,
  CheckCircle2,
  Layers,
  ArrowRight,
  Download,
  Bell,
  ChevronDown,
  ChevronUp,
  MessageSquare,
  Calendar,
  BarChart3,
} from 'lucide-react'
import { TrackerApplication } from '../types'
import { exportApplicationsCSV } from '../api'

interface TrackerKanbanProps {
  applications: TrackerApplication[]
  onUpdateStatus: (jobId: string, newStatus: string, notes?: string) => void
  onDelete: (jobId: string) => void
  onSelectJobForReview: (jobId: string) => void
  darkMode: boolean
}

const STAGES = [
  { id: 'saved', title: 'Saved Jobs', borderTop: 'border-t-slate-400', badge: 'bg-slate-100 text-slate-700 border border-slate-200' },
  { id: 'applied', title: 'Applied', borderTop: 'border-t-[#0a66c2]', badge: 'bg-blue-50 text-[#0a66c2] border border-blue-200' },
  { id: 'interviewing', title: 'Interviewing', borderTop: 'border-t-purple-600', badge: 'bg-purple-50 text-purple-700 border border-purple-200' },
  { id: 'offer', title: 'Job Offers', borderTop: 'border-t-[#057642]', badge: 'bg-emerald-50 text-[#057642] border border-emerald-200' },
  { id: 'rejected', title: 'Archived', borderTop: 'border-t-slate-300', badge: 'bg-slate-100 text-slate-500 border border-slate-200' },
]

function getLatestNote(notes: TrackerApplication['notes']): string | null {
  if (!notes) return null
  if (typeof notes === 'string') return notes
  if (Array.isArray(notes) && notes.length > 0) {
    return notes[notes.length - 1].text
  }
  return null
}

function getOverdueFollowups(followups?: TrackerApplication['followup_dates']): number {
  if (!followups) return 0
  const now = new Date()
  return followups.filter((f) => !f.completed && new Date(f.date) < now).length
}

export const TrackerKanban: React.FC<TrackerKanbanProps> = ({
  applications,
  onUpdateStatus,
  onDelete,
  onSelectJobForReview,
  darkMode,
}) => {
  const [expandedInterviews, setExpandedInterviews] = useState<Set<string>>(new Set())

  const toggleInterviewExpand = (jobId: string) => {
    setExpandedInterviews((prev) => {
      const next = new Set(prev)
      if (next.has(jobId)) {
        next.delete(jobId)
      } else {
        next.add(jobId)
      }
      return next
    })
  }

  // Pipeline stats
  const totalApps = applications.length
  const appliedCount = applications.filter((a) => a.status === 'applied' || a.status === 'ready_for_review').length
  const interviewingCount = applications.filter((a) => a.status === 'interviewing').length
  const offerCount = applications.filter((a) => a.status === 'offer').length
  const responseRate = totalApps > 0 ? Math.round(((interviewingCount + offerCount) / Math.max(appliedCount, 1)) * 100) : 0

  return (
    <div className={`h-[calc(100vh-3.5rem)] overflow-y-auto p-4 sm:p-6 flex flex-col ${darkMode ? 'bg-[#1a1a2e]' : 'bg-[#f4f2ee]'}`}>
      <div className="max-w-7xl w-full mx-auto flex flex-col flex-1">
        {/* Header Bar */}
        <div className={`rounded-xl border p-4 sm:p-5 mb-5 flex flex-wrap items-center justify-between gap-3 shadow-xs ${
          darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'
        }`}>
          <div>
            <div className="flex items-center gap-2">
              <span className={`p-1.5 rounded-lg ${darkMode ? 'bg-[#1e3a5f] text-[#0a66c2]' : 'bg-[#edf3f8] text-[#0a66c2]'}`}>
                <Layers className="w-4 h-4" />
              </span>
              <h2 className={`text-lg font-bold tracking-tight ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>
                My Job Applications Pipeline
              </h2>
            </div>
            <p className={`text-xs mt-1 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
              Organize interview stages, tailor follow-ups, and monitor status across all ATS boards.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-xs font-semibold px-3 py-1.5 rounded-full border ${
              darkMode ? 'bg-[#1e3a5f] text-[#0a66c2] border-[#2a4a6f]' : 'bg-[#edf3f8] text-[#0a66c2] border-[#d0e2f5]'
            }`}>
              {applications.length} Tracked Roles
            </span>
            <button
              onClick={() => exportApplicationsCSV(applications)}
              className={`px-3.5 py-1.5 rounded-full text-xs font-bold flex items-center gap-1.5 shadow-xs cursor-pointer transition-all ${
                darkMode ? 'bg-[#1e3a5f] hover:bg-[#243f63] text-slate-200 border border-[#2a4a6f]' : 'bg-white hover:bg-slate-50 text-slate-700 border border-slate-300'
              }`}
            >
              <Download className="w-3.5 h-3.5" />
              Export CSV
            </button>
          </div>
        </div>

        {/* Pipeline Stats Bar */}
        <div className={`rounded-xl border p-3 mb-5 flex flex-wrap items-center gap-4 shadow-xs ${
          darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'
        }`}>
          <div className="flex items-center gap-2">
            <BarChart3 className={`w-4 h-4 ${darkMode ? 'text-[#0a66c2]' : 'text-[#0a66c2]'}`} />
            <span className={`text-xs font-bold ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>Pipeline Stats</span>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <span className={`px-2.5 py-1 rounded-full font-semibold ${darkMode ? 'bg-[#1e3a5f] text-slate-300' : 'bg-slate-100 text-slate-700'}`}>
              Total: {totalApps}
            </span>
            <span className="px-2.5 py-1 rounded-full font-semibold bg-blue-50 text-blue-700">
              Applied: {appliedCount}
            </span>
            <span className="px-2.5 py-1 rounded-full font-semibold bg-purple-50 text-purple-700">
              Interviewing: {interviewingCount}
            </span>
            <span className="px-2.5 py-1 rounded-full font-semibold bg-emerald-50 text-emerald-700">
              Offers: {offerCount}
            </span>
            <span className={`px-2.5 py-1 rounded-full font-semibold ${
              responseRate > 30 ? 'bg-emerald-50 text-emerald-700' : responseRate > 10 ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-600'
            }`}>
              Response Rate: {responseRate}%
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
                className={`flex-1 rounded-xl border flex flex-col overflow-hidden shadow-2xs ${
                  darkMode ? 'bg-[#16213e]/70 border-[#1e3a5f]/80' : 'bg-[#ebedf0]/70 border-slate-200/80'
                }`}
              >
                {/* Column Header */}
                <div
                  className={`px-4 py-3 border-b flex items-center justify-between border-t-4 ${stage.borderTop} ${
                    darkMode ? 'bg-[#16213e] border-b-[#1e3a5f]' : 'bg-white border-b-slate-200'
                  }`}
                >
                  <span className={`font-bold text-xs tracking-tight ${darkMode ? 'text-slate-200' : 'text-slate-900'}`}>
                    {stage.title}
                  </span>
                  <span className={`text-[11px] px-2 py-0.5 rounded-full font-bold ${stage.badge}`}>
                    {stageApps.length}
                  </span>
                </div>

                {/* Column Cards */}
                <div className="flex-1 p-3 overflow-y-auto space-y-3">
                  {stageApps.length === 0 ? (
                    <div className={`text-center py-10 text-xs ${darkMode ? 'text-slate-500' : 'text-slate-400'}`}>
                      No jobs in this stage
                    </div>
                  ) : (
                    stageApps.map((app) => {
                      const overdueCount = getOverdueFollowups(app.followup_dates)
                      const latestNote = getLatestNote(app.notes)
                      const isInterviewExpanded = expandedInterviews.has(app.job_id)

                      return (
                        <div
                          key={app.job_id}
                          className={`p-4 rounded-xl border space-y-3 transition-all shadow-2xs group ${
                            darkMode
                              ? 'bg-[#16213e] border-[#1e3a5f] hover:border-[#0a66c2] hover:shadow-sm'
                              : 'bg-white border-slate-200 hover:border-[#0a66c2] hover:shadow-sm'
                          }`}
                        >
                          <div
                            className="cursor-pointer"
                            onClick={() => onSelectJobForReview(app.job_id)}
                          >
                            <div className="flex items-center justify-between">
                              <h4 className={`text-sm font-semibold group-hover:text-[#0a66c2] transition-colors line-clamp-1 ${
                                darkMode ? 'text-slate-100' : 'text-slate-900'
                              }`}>
                                {app.title}
                              </h4>
                              {/* Overdue Follow-up Badge */}
                              {overdueCount > 0 && (
                                <span className="flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 text-[10px] font-bold shrink-0">
                                  <Bell className="w-3 h-3" />
                                  {overdueCount}
                                </span>
                              )}
                            </div>
                            <p className={`text-xs font-normal flex items-center gap-1.5 mt-0.5 ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
                              <Building2 className={`w-3.5 h-3.5 ${darkMode ? 'text-slate-500' : 'text-slate-400'}`} />
                              {app.company}
                            </p>
                          </div>

                          {/* Latest Note */}
                          {latestNote && (
                            <div className={`flex items-start gap-1.5 text-[11px] px-2 py-1.5 rounded-lg ${
                              darkMode ? 'bg-[#1e3a5f] text-slate-300' : 'bg-slate-50 text-slate-600'
                            }`}>
                              <MessageSquare className="w-3 h-3 shrink-0 mt-0.5 text-slate-400" />
                              <span className="line-clamp-2">{latestNote}</span>
                            </div>
                          )}

                          {/* Interview Timeline (collapsed by default) */}
                          {app.interview_stages && app.interview_stages.length > 0 && (
                            <div>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  toggleInterviewExpand(app.job_id)
                                }}
                                className={`flex items-center gap-1 text-[11px] font-semibold cursor-pointer ${
                                  darkMode ? 'text-[#0a66c2]' : 'text-[#0a66c2]'
                                }`}
                              >
                                <Calendar className="w-3 h-3" />
                                {app.interview_stages.length} Interview Stage{app.interview_stages.length > 1 ? 's' : ''}
                                {isInterviewExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                              </button>

                              {isInterviewExpanded && (
                                <div className="mt-2 ml-1 border-l-2 border-purple-300 pl-3 space-y-2">
                                  {app.interview_stages.map((stage, idx) => (
                                    <div key={idx} className="relative">
                                      <div className="absolute -left-[17px] top-1 w-2.5 h-2.5 rounded-full bg-purple-400 border-2 border-white" />
                                      <p className={`text-[11px] font-semibold ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>
                                        {stage.stage}
                                      </p>
                                      <p className={`text-[10px] ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                                        {new Date(stage.date).toLocaleDateString()}
                                        {stage.notes && ` - ${stage.notes}`}
                                      </p>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}

                          {/* Match & Date Line */}
                          <div className={`flex items-center justify-between text-[11px] pt-1 border-t ${
                            darkMode ? 'border-[#1e3a5f] text-slate-400' : 'border-slate-100 text-slate-500'
                          }`}>
                            {app.coverage_score ? (
                              <span className="flex items-center gap-1 text-[#057642] font-semibold bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                                <CheckCircle2 className="w-3 h-3" />
                                {Math.round(app.coverage_score * 100)}% Match
                              </span>
                            ) : (
                              <span className={`px-2 py-0.5 rounded-full font-medium ${
                                darkMode ? 'bg-[#1e3a5f] text-slate-400' : 'bg-slate-100 text-slate-600'
                              }`}>
                                Tracked
                              </span>
                            )}

                            {app.updated_at && (
                              <span className={`flex items-center gap-1 text-[10px] ${darkMode ? 'text-slate-500' : 'text-slate-400'}`}>
                                <Clock className="w-3 h-3" />
                                {new Date(app.updated_at).toLocaleDateString()}
                              </span>
                            )}
                          </div>

                          {/* Stage Dropdown & Action Links */}
                          <div className={`pt-2 border-t flex items-center justify-between gap-2 ${darkMode ? 'border-[#1e3a5f]' : 'border-slate-100'}`}>
                            <select
                              value={app.status}
                              onChange={(e) => onUpdateStatus(app.job_id, e.target.value)}
                              className={`border border-transparent text-xs font-semibold rounded-full px-2.5 py-1 focus:outline-none cursor-pointer transition-colors ${
                                darkMode
                                  ? 'bg-[#1e3a5f] hover:bg-[#243f63] focus:border-[#0a66c2] text-slate-300'
                                  : 'bg-[#edf3f8] hover:bg-[#e4ebf2] focus:border-[#0a66c2] text-slate-700'
                              }`}
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
                                className={`p-1.5 rounded-full transition-colors ${
                                  darkMode ? 'text-slate-400 hover:text-[#0a66c2] hover:bg-[#1e3a5f]' : 'text-slate-400 hover:text-[#0a66c2] hover:bg-slate-100'
                                }`}
                                title="Review Job Details"
                              >
                                <ArrowRight className="w-3.5 h-3.5" />
                              </button>

                              {app.application_url && (
                                <a
                                  href={app.application_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className={`p-1.5 rounded-full transition-colors ${
                                    darkMode ? 'text-slate-400 hover:text-[#0a66c2] hover:bg-[#1e3a5f]' : 'text-slate-400 hover:text-[#0a66c2] hover:bg-slate-100'
                                  }`}
                                  title="Open Job Application"
                                >
                                  <ExternalLink className="w-3.5 h-3.5" />
                                </a>
                              )}

                              <button
                                onClick={() => onDelete(app.job_id)}
                                className={`p-1.5 rounded-full transition-colors ${
                                  darkMode ? 'text-slate-400 hover:text-rose-400 hover:bg-rose-900/30' : 'text-slate-400 hover:text-rose-600 hover:bg-rose-50'
                                }`}
                                title="Remove from Pipeline"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>
                        </div>
                      )
                    })
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
