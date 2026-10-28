import React, { useState, useMemo, useEffect } from 'react'
import { Briefcase } from 'lucide-react'
import { JobListing, JobOutput } from '../types'
import { DetailTab } from './job_split/helpers'
import { JobFilterBar } from './job_split/JobFilterBar'
import { JobListPane } from './job_split/JobListPane'
import { JobDetailHeader } from './job_split/JobDetailHeader'
import { MatchIntelligenceCard } from './job_split/MatchIntelligenceCard'
import { JobDetailTabs } from './job_split/JobDetailTabs'

export interface JobSplitViewProps {
  jobs: JobListing[]
  selectedJob: JobListing | null
  onSelectJob: (job: JobListing) => void
  onTailor: (job: JobListing, coverLetter: boolean) => Promise<void>
  onTrack: (job: JobListing, status: string) => void
  onAutoApply?: (job: JobListing, autoSubmit?: boolean) => Promise<void>
  isAutoApplying?: boolean
  activeJobIdAutoApplying?: string | null
  tailoredOutput: JobOutput | null
  isTailoring: boolean
  activeJobIdTailoring: string | null
  bulkTailorIds: Set<string>
  onToggleBulkId: (jobId: string) => void
  onBulkTailor: (coverLetter?: boolean) => void
  darkMode: boolean
}

export const JobSplitView: React.FC<JobSplitViewProps> = ({
  jobs,
  selectedJob,
  onSelectJob,
  onTailor,
  onTrack,
  onAutoApply,
  isAutoApplying,
  activeJobIdAutoApplying,
  tailoredOutput,
  isTailoring,
  activeJobIdTailoring,
  bulkTailorIds,
  onToggleBulkId,
  onBulkTailor,
  darkMode,
}) => {
  // Filter states
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedPlatform, setSelectedPlatform] = useState<string>('all')
  const [selectedCompany, setSelectedCompany] = useState<string>('all')
  const [remoteOnly, setRemoteOnly] = useState<boolean>(false)
  const [minScoreFilter, setMinScoreFilter] = useState<number>(0)
  const [tailoredOnly, setTailoredOnly] = useState<boolean>(false)
  const [minSalaryFilter, setMinSalaryFilter] = useState<number>(0)
  const [postedWithin, setPostedWithin] = useState<number>(0)
  const [isBulkMode, setIsBulkMode] = useState<boolean>(false)

  // Subtabs state
  const [activeTab, setActiveTab] = useState<DetailTab>('jd')

  // Pagination state
  const [currentPage, setCurrentPage] = useState<number>(1)
  const [pageSize, setPageSize] = useState<number>(15)

  // Reset detail tab to 'jd' when selected job changes
  useEffect(() => {
    setActiveTab('jd')
  }, [selectedJob?.id])

  // Available filters computed from full jobs list
  const availablePlatforms = useMemo(() => {
    const set = new Set<string>()
    jobs.forEach((j) => {
      if (j.ats_source) set.add(j.ats_source)
    })
    return Array.from(set).sort()
  }, [jobs])

  const availableCompanies = useMemo(() => {
    const set = new Set<string>()
    jobs.forEach((j) => {
      if (j.company) set.add(j.company)
    })
    return Array.from(set).sort()
  }, [jobs])

  // Filtered jobs
  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
      if (searchQuery) {
        const q = searchQuery.toLowerCase()
        const matchesTitle = job.title.toLowerCase().includes(q)
        const matchesCompany = job.company.toLowerCase().includes(q)
        const matchesLocation = (job.location || '').toLowerCase().includes(q)
        if (!matchesTitle && !matchesCompany && !matchesLocation) return false
      }
      if (selectedPlatform !== 'all' && job.ats_source !== selectedPlatform) return false
      if (selectedCompany !== 'all' && job.company !== selectedCompany) return false
      if (remoteOnly && !job.remote) return false
      if (minScoreFilter > 0 && (job.score || 0) < minScoreFilter) return false
      if (tailoredOnly && !job.has_tailored_resume) return false
      if (minSalaryFilter > 0 && job.salary_range) {
        const minSal = job.salary_range.min || 0
        if (minSal < minSalaryFilter * 1000) return false
      }
      if (postedWithin > 0 && job.posted_date) {
        const posted = new Date(job.posted_date)
        const now = new Date()
        const diffDays = Math.floor((now.getTime() - posted.getTime()) / (1000 * 60 * 60 * 24))
        if (diffDays > postedWithin) return false
      }
      return true
    })
  }, [
    jobs,
    searchQuery,
    selectedPlatform,
    selectedCompany,
    remoteOnly,
    minScoreFilter,
    tailoredOnly,
    minSalaryFilter,
    postedWithin,
  ])

  useEffect(() => {
    setCurrentPage(1)
  }, [
    searchQuery,
    selectedPlatform,
    selectedCompany,
    remoteOnly,
    minScoreFilter,
    tailoredOnly,
    minSalaryFilter,
    postedWithin,
  ])

  const totalPages = Math.max(1, Math.ceil(filteredJobs.length / (pageSize || 1)))
  const paginatedJobs = useMemo(() => {
    if (pageSize <= 0) return filteredJobs
    const start = (currentPage - 1) * pageSize
    return filteredJobs.slice(start, start + pageSize)
  }, [filteredJobs, currentPage, pageSize])

  const activeJob = selectedJob || filteredJobs[0] || null

  const hasActiveFilters =
    searchQuery !== '' ||
    selectedPlatform !== 'all' ||
    selectedCompany !== 'all' ||
    remoteOnly ||
    minScoreFilter > 0 ||
    tailoredOnly ||
    minSalaryFilter > 0 ||
    postedWithin > 0

  const handleClearFilters = () => {
    setSearchQuery('')
    setSelectedPlatform('all')
    setSelectedCompany('all')
    setRemoteOnly(false)
    setMinScoreFilter(0)
    setTailoredOnly(false)
    setMinSalaryFilter(0)
    setPostedWithin(0)
  }

  const handleSelectAllBulk = () => {
    paginatedJobs.forEach((j) => {
      if (!bulkTailorIds.has(j.id)) onToggleBulkId(j.id)
    })
  }

  const handleDeselectAllBulk = () => {
    paginatedJobs.forEach((j) => {
      if (bulkTailorIds.has(j.id)) onToggleBulkId(j.id)
    })
  }

  return (
    <div className={`flex flex-col h-[calc(100vh-3.5rem)] overflow-hidden ${darkMode ? 'bg-[#1a1a2e]' : 'bg-[#f4f2ee]'}`}>
      {/* 1. Top Filter Bar */}
      <JobFilterBar
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        postedWithin={postedWithin}
        setPostedWithin={setPostedWithin}
        minScoreFilter={minScoreFilter}
        setMinScoreFilter={setMinScoreFilter}
        remoteOnly={remoteOnly}
        setRemoteOnly={setRemoteOnly}
        selectedCompany={selectedCompany}
        setSelectedCompany={setSelectedCompany}
        availableCompanies={availableCompanies}
        selectedPlatform={selectedPlatform}
        setSelectedPlatform={setSelectedPlatform}
        availablePlatforms={availablePlatforms}
        minSalaryFilter={minSalaryFilter}
        setMinSalaryFilter={setMinSalaryFilter}
        tailoredOnly={tailoredOnly}
        setTailoredOnly={setTailoredOnly}
        isBulkMode={isBulkMode}
        setIsBulkMode={setIsBulkMode}
        darkMode={darkMode}
        hasActiveFilters={hasActiveFilters}
        onClearFilters={handleClearFilters}
      />

      {/* 2. Main Two-Column Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Column: Job Matches List */}
        <JobListPane
          filteredJobs={filteredJobs}
          paginatedJobs={paginatedJobs}
          activeJob={activeJob}
          onSelectJob={onSelectJob}
          isBulkMode={isBulkMode}
          bulkTailorIds={bulkTailorIds}
          onToggleBulkId={onToggleBulkId}
          onBulkTailor={onBulkTailor}
          onSelectAllBulk={handleSelectAllBulk}
          onDeselectAllBulk={handleDeselectAllBulk}
          isTailoring={isTailoring}
          currentPage={currentPage}
          setCurrentPage={setCurrentPage}
          totalPages={totalPages}
          pageSize={pageSize}
          setPageSize={setPageSize}
          darkMode={darkMode}
        />

        {/* Right Column: Active Job Detail */}
        <div className={`flex-1 flex flex-col overflow-hidden ${darkMode ? 'bg-[#1a1a2e]' : 'bg-white'}`}>
          {activeJob ? (
            <div className="flex-1 overflow-y-auto">
              {/* Job Header */}
              <JobDetailHeader
                job={activeJob}
                onAutoApply={onAutoApply}
                isAutoApplying={isAutoApplying}
                activeJobIdAutoApplying={activeJobIdAutoApplying}
                onTailor={onTailor}
                isTailoring={isTailoring}
                activeJobIdTailoring={activeJobIdTailoring}
                onTrack={onTrack}
                darkMode={darkMode}
              />

              <div className="p-6 space-y-6">
                {/* Premium Match Intelligence Card */}
                <MatchIntelligenceCard
                  job={activeJob}
                  onShowValidation={() => setActiveTab('validation')}
                  onTailorResume={() => onTailor(activeJob, false)}
                />

                {/* Subtabs and Tab Bodies */}
                <JobDetailTabs
                  activeTab={activeTab}
                  setActiveTab={setActiveTab}
                  job={activeJob}
                  tailoredOutput={tailoredOutput}
                  onTailor={onTailor}
                  darkMode={darkMode}
                />
              </div>
            </div>
          ) : jobs.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center p-8">
              <Briefcase className={`w-16 h-16 mb-4 ${darkMode ? 'text-slate-600' : 'text-slate-200'}`} />
              <p className={`font-bold text-lg ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>No jobs scanned yet</p>
              <p className={`text-sm mt-2 text-center max-w-sm ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                Configure your ATS board links in Settings, then click "Scan ATS Boards" to discover matching roles.
              </p>
            </div>
          ) : (
            <div className="p-6 space-y-6 animate-pulse">
              <div className="h-14 w-14 rounded-lg bg-slate-200 dark:bg-slate-700" />
              <div className="h-6 w-64 bg-slate-200 dark:bg-slate-700 rounded" />
              <div className="h-32 w-full bg-slate-200 dark:bg-slate-700 rounded-xl" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
