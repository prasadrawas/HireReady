import React from 'react'
import { CheckSquare, Square, Sparkles, ChevronRight, Briefcase } from 'lucide-react'
import { JobListing } from '../../types'
import { CompanyLogo } from '../CompanyLogo'
import { getDaysAgo } from './helpers'

interface JobListPaneProps {
  filteredJobs: JobListing[]
  paginatedJobs: JobListing[]
  activeJob: JobListing | null
  onSelectJob: (job: JobListing) => void
  isBulkMode: boolean
  bulkTailorIds: Set<string>
  onToggleBulkId: (jobId: string) => void
  onBulkTailor: (coverLetter?: boolean) => void
  onSelectAllBulk: () => void
  onDeselectAllBulk: () => void
  isTailoring: boolean
  currentPage: number
  setCurrentPage: (page: number | ((prev: number) => number)) => void
  totalPages: number
  pageSize: number
  setPageSize: (size: number) => void
  darkMode: boolean
}

export const JobListPane: React.FC<JobListPaneProps> = ({
  filteredJobs,
  paginatedJobs,
  activeJob,
  onSelectJob,
  isBulkMode,
  bulkTailorIds,
  onToggleBulkId,
  onBulkTailor,
  onSelectAllBulk,
  onDeselectAllBulk,
  isTailoring,
  currentPage,
  setCurrentPage,
  totalPages,
  pageSize,
  setPageSize,
  darkMode,
}) => {
  return (
    <div
      className={`w-full md:w-[420px] lg:w-[460px] border-r flex flex-col shrink-0 overflow-hidden ${
        darkMode ? 'border-[#1e3a5f] bg-[#16213e]' : 'border-slate-200 bg-white'
      }`}
    >
      {/* List Header */}
      <div
        className={`px-4 py-3 border-b flex items-center justify-between shrink-0 ${
          darkMode ? 'border-[#1e3a5f] bg-[#1a1a2e]' : 'border-slate-100 bg-[#fcfbfa]'
        }`}
      >
        <div className="flex items-center gap-2">
          <span className={`text-xs font-bold ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>
            Top Job Matches
          </span>
          <span
            className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
              darkMode ? 'bg-[#1e3a5f] text-slate-300' : 'bg-slate-200 text-slate-700'
            }`}
          >
            {filteredJobs.length}
          </span>
        </div>
        <span className={`text-[11px] ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
          Sorted by AI Match
        </span>
      </div>

      {/* Bulk Action Banner */}
      {isBulkMode && (
        <div className="px-4 py-2.5 bg-purple-50 border-b border-purple-200 flex items-center justify-between text-xs shrink-0">
          <div className="flex items-center gap-2">
            <span className="font-bold text-purple-900">{bulkTailorIds.size} selected</span>
            <button onClick={onSelectAllBulk} className="text-purple-700 underline font-semibold cursor-pointer">
              Select page
            </button>
            <span className="text-purple-300">|</span>
            <button onClick={onDeselectAllBulk} className="text-purple-700 underline font-semibold cursor-pointer">
              Deselect
            </button>
          </div>
          <button
            onClick={() => onBulkTailor(false)}
            disabled={bulkTailorIds.size === 0 || isTailoring}
            className="px-3 py-1 rounded-full bg-purple-700 hover:bg-purple-800 text-white font-bold text-xs flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            <Sparkles className="w-3 h-3" />
            <span>{isTailoring ? 'Tailoring...' : 'Tailor All'}</span>
          </button>
        </div>
      )}

      {/* Scrollable Job List */}
      <div className="flex-1 overflow-y-auto divide-y divide-slate-100 dark:divide-[#1e3a5f]">
        {paginatedJobs.length === 0 ? (
          <div className="p-8 text-center">
            <Briefcase className={`w-8 h-8 mx-auto mb-2 ${darkMode ? 'text-slate-600' : 'text-slate-300'}`} />
            <p className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>No jobs match current filters.</p>
          </div>
        ) : (
          paginatedJobs.map((job) => {
            const isSelected = activeJob?.id === job.id
            const isChecked = bulkTailorIds.has(job.id)
            const daysAgo = getDaysAgo(job.posted_date)

            return (
              <div
                key={job.id}
                onClick={() => {
                  if (isBulkMode) onToggleBulkId(job.id)
                  else onSelectJob(job)
                }}
                className={`p-4 transition-all cursor-pointer relative flex items-start gap-3 border-l-4 ${
                  isSelected
                    ? darkMode
                      ? 'bg-[#1e3a5f] border-l-[#0a66c2]'
                      : 'bg-[#edf3f8] border-l-[#0a66c2]'
                    : darkMode
                    ? 'border-l-transparent hover:bg-[#1e3a5f]/50'
                    : 'border-l-transparent hover:bg-slate-50'
                }`}
              >
                {/* Bulk Select Checkbox */}
                {isBulkMode && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onToggleBulkId(job.id)
                    }}
                    className="mt-1 text-purple-700 shrink-0 cursor-pointer"
                  >
                    {isChecked ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
                  </button>
                )}

                {/* Company Logo */}
                <CompanyLogo
                  company={job.company}
                  companySlug={job.company_slug}
                  className="w-11 h-11 rounded-lg text-sm shrink-0"
                />

                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <h3
                      className={`text-sm font-bold truncate leading-snug ${
                        isSelected ? 'text-[#0a66c2]' : darkMode ? 'text-slate-100' : 'text-slate-900'
                      }`}
                    >
                      {job.title}
                    </h3>
                  </div>

                  <p className={`text-xs mt-0.5 truncate font-medium ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>
                    {job.company}
                  </p>

                  <p className={`text-[11px] truncate mt-0.5 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                    {job.location || 'Location unlisted'}
                  </p>

                  {/* Badges Row */}
                  <div className="flex flex-wrap items-center gap-1.5 mt-2">
                    {/* Match Score */}
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        (job.score || 0) >= 0.7
                          ? 'bg-emerald-100 text-emerald-800'
                          : (job.score || 0) >= 0.5
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-indigo-50 text-indigo-700'
                      }`}
                    >
                      {Math.round((job.score || 0.5) * 100)}% match
                    </span>

                    {/* Tailored Badge */}
                    {job.has_tailored_resume && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-100 text-purple-800">
                        Tailored
                      </span>
                    )}

                    {/* Remote Pill */}
                    {job.remote && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-300 dark:bg-emerald-950 dark:text-emerald-200 dark:border-emerald-800">
                        Remote
                      </span>
                    )}

                    {/* Secondary location indicator */}
                    {job.locations && job.locations.length > 1 && (
                      <span
                        className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-950 dark:text-indigo-200 dark:border-indigo-800"
                        title={job.locations.join(', ')}
                      >
                        +{job.locations.length - 1} loc
                      </span>
                    )}

                    {/* Equity Pill */}
                    {job.has_equity && (
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-300 dark:bg-amber-950 dark:text-amber-200 dark:border-amber-800">
                        ★ Equity
                      </span>
                    )}

                    {/* Days Ago */}
                    {daysAgo && (
                      <span className={`text-[10px] ml-auto ${darkMode ? 'text-slate-400' : 'text-slate-400'}`}>
                        {daysAgo}
                      </span>
                    )}
                  </div>
                </div>

                <ChevronRight
                  className={`w-4 h-4 shrink-0 mt-2 ${
                    isSelected ? 'text-[#0a66c2]' : darkMode ? 'text-slate-600' : 'text-slate-300'
                  }`}
                />
              </div>
            )
          })
        )}
      </div>

      {/* Pagination Bar */}
      {filteredJobs.length > 0 && (
        <div
          className={`px-3 py-2 border-t flex flex-wrap items-center justify-between gap-2 text-xs shrink-0 ${
            darkMode ? 'border-[#1e3a5f] bg-[#1a1a2e] text-slate-300' : 'border-slate-200 bg-[#fcfbfa] text-slate-600'
          }`}
        >
          {/* Page size selector */}
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] font-medium">Show:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(parseInt(e.target.value))
                setCurrentPage(1)
              }}
              className={`rounded-md px-1.5 py-0.5 text-xs font-semibold focus:outline-none cursor-pointer border ${
                darkMode ? 'bg-[#16213e] text-slate-300 border-[#1e3a5f]' : 'bg-white text-slate-700 border-slate-300'
              }`}
            >
              <option value={10}>10</option>
              <option value={15}>15</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={0}>All</option>
            </select>
          </div>

          {/* Page buttons */}
          {pageSize > 0 && totalPages > 1 && (
            <div className="flex items-center gap-1">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage <= 1}
                className={`px-2 py-0.5 rounded border text-[11px] font-semibold cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${
                  darkMode
                    ? 'border-[#1e3a5f] hover:bg-[#1e3a5f] text-slate-300'
                    : 'border-slate-300 hover:bg-slate-100 text-slate-700'
                }`}
              >
                Prev
              </button>

              <span className="text-[11px] font-semibold px-1">
                {currentPage} / {totalPages}
              </span>

              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage >= totalPages}
                className={`px-2 py-0.5 rounded border text-[11px] font-semibold cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${
                  darkMode
                    ? 'border-[#1e3a5f] hover:bg-[#1e3a5f] text-slate-300'
                    : 'border-slate-300 hover:bg-slate-100 text-slate-700'
                }`}
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

