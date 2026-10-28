import React, { useState, useEffect } from 'react'
import { Navbar } from './components/Navbar'
import { JobSplitView } from './components/JobSplitView'
import { TrackerKanban } from './components/TrackerKanban'
import { TailorStudio } from './components/TailorStudio'
import { MasterResumeView } from './components/MasterResumeView'
import { SettingsView } from './components/SettingsView'
import { ScanModal } from './components/ScanModal'
import {
  fetchJobs,
  fetchStats,
  fetchTracker,
  fetchJobOutput,
  tailorJob,
  tailorBulk,
  triggerAutoApply,
  updateTrackerStatus,
  deleteTrackerJob,
} from './api'
import { JobListing, JobOutput, TrackerApplication } from './types'

export function App() {
  const [activeTab, setActiveTab] = useState<'jobs' | 'pipeline' | 'studio' | 'master_resume' | 'settings'>('jobs')
  const [jobs, setJobs] = useState<JobListing[]>([])
  const [applications, setApplications] = useState<TrackerApplication[]>([])
  const [selectedJob, setSelectedJob] = useState<JobListing | null>(null)
  const [tailoredOutput, setTailoredOutput] = useState<JobOutput | null>(null)
  const [isScanningModalOpen, setIsScanningModalOpen] = useState(false)
  const [isScanning, setIsScanning] = useState(false)
  const [isTailoring, setIsTailoring] = useState(false)
  const [activeJobIdTailoring, setActiveJobIdTailoring] = useState<string | null>(null)
  const [isAutoApplying, setIsAutoApplying] = useState(false)
  const [activeJobIdAutoApplying, setActiveJobIdAutoApplying] = useState<string | null>(null)
  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'error'; undoAction?: () => void } | null>(null)
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    try {
      return localStorage.getItem('hireready_darkmode') === 'true'
    } catch {
      return false
    }
  })
  const [bulkTailorIds, setBulkTailorIds] = useState<Set<string>>(new Set())

  // Persist dark mode
  useEffect(() => {
    try {
      localStorage.setItem('hireready_darkmode', darkMode.toString())
    } catch {}
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

  // Page title based on active tab
  useEffect(() => {
    const titles: Record<string, string> = {
      jobs: 'Jobs - HireReady',
      pipeline: 'Pipeline - HireReady',
      studio: 'Tailor Studio - HireReady',
      settings: 'Settings - HireReady',
    }
    document.title = titles[activeTab] || 'HireReady — AI Resume Pipeline'
  }, [activeTab])

  useEffect(() => {
    loadInitialData()
  }, [])

  // Whenever selectedJob changes, fetch tailored assets if they exist
  useEffect(() => {
    if (selectedJob) {
      loadJobOutput(selectedJob.id)
    } else {
      setTailoredOutput(null)
    }
  }, [selectedJob])

  const loadInitialData = async () => {
    try {
      const [jobsData, trackerData] = await Promise.all([
        fetchJobs(),
        fetchTracker(),
      ])
      setJobs(jobsData.jobs || [])
      setApplications(trackerData.applications || [])
      if (jobsData.jobs && jobsData.jobs.length > 0 && !selectedJob) {
        setSelectedJob(jobsData.jobs[0])
      }
    } catch (err) {
      console.error('Error loading initial data:', err)
    }
  }

  const loadJobOutput = async (jobId: string) => {
    try {
      const output = await fetchJobOutput(jobId)
      setTailoredOutput(output)
    } catch (err) {
      setTailoredOutput(null)
    }
  }

  const showNotification = (message: string, type: 'success' | 'error' = 'success', undoAction?: () => void) => {
    setNotification({ message, type, undoAction })
    setTimeout(() => setNotification(null), 4500)
  }

  const handleSelectJob = (job: JobListing) => {
    setSelectedJob(job)
  }

  const handleTailor = async (job: JobListing, coverLetter: boolean) => {
    setIsTailoring(true)
    setActiveJobIdTailoring(job.id)
    try {
      const res = await tailorJob(job.id, coverLetter)
      setTailoredOutput(res.data)

      // Update local job tailored status
      setJobs((prev) =>
        prev.map((j) => (j.id === job.id ? { ...j, has_tailored_resume: true } : j))
      )
      if (selectedJob?.id === job.id) {
        setSelectedJob((prev) => (prev ? { ...prev, has_tailored_resume: true } : null))
      }

      // Refresh applications tracker
      const trackerData = await fetchTracker()
      setApplications(trackerData.applications || [])

      showNotification(`Tailored resume & assets created for ${job.company} - ${job.title}!`)
    } catch (err: any) {
      console.error('Tailor error:', err)
      showNotification(err.message || 'Failed to tailor resume', 'error')
    } finally {
      setIsTailoring(false)
      setActiveJobIdTailoring(null)
    }
  }

  const handleBulkTailor = async (coverLetter = false) => {
    if (bulkTailorIds.size === 0) return
    setIsTailoring(true)
    const ids = Array.from(bulkTailorIds)
    try {
      const { results } = await tailorBulk(ids, coverLetter)
      const successCount = Object.values(results).filter((r: any) => r.success).length
      const failCount = Object.values(results).filter((r: any) => !r.success).length

      // Update local job tailored status for successful ones
      setJobs((prev) =>
        prev.map((j) => {
          if (results[j.id]?.success) {
            return { ...j, has_tailored_resume: true }
          }
          return j
        })
      )

      // Refresh applications tracker
      const trackerData = await fetchTracker()
      setApplications(trackerData.applications || [])

      setBulkTailorIds(new Set())

      if (failCount > 0) {
        showNotification(`Bulk tailor: ${successCount} succeeded, ${failCount} failed`, failCount > successCount ? 'error' : 'success')
      } else {
        showNotification(`Bulk tailor complete: ${successCount} resumes tailored!`)
      }
    } catch (err: any) {
      console.error('Bulk tailor error:', err)
      showNotification(err.message || 'Bulk tailor failed', 'error')
    } finally {
      setIsTailoring(false)
    }
  }

  const handleAutoApply = async (job: JobListing, autoSubmit = false) => {
    setIsAutoApplying(true)
    setActiveJobIdAutoApplying(job.id)
    try {
      showNotification(`Launching browser & auto-filling application for ${job.company}...`)
      const res = await triggerAutoApply(job.id, autoSubmit)
      if (res.success) {
        // Refresh applications tracker
        const trackerData = await fetchTracker()
        setApplications(trackerData.applications || [])
        // Update job tracker status locally
        const newStatus = res.data?.status === 'submitted' ? 'submitted' : 'ready_for_review'
        setJobs((prev) =>
          prev.map((j) => (j.id === job.id ? { ...j, tracker_status: newStatus, has_tailored_resume: true } : j))
        )
        if (selectedJob?.id === job.id) {
          setSelectedJob((prev) =>
            prev ? { ...prev, tracker_status: newStatus, has_tailored_resume: true } : null
          )
        }
        showNotification(res.data?.message || `Auto-applied successfully to ${job.company}!`)
      } else {
        showNotification(res.data?.message || 'Auto-apply encountered an issue', 'error')
      }
    } catch (err: any) {
      console.error('Auto-apply error:', err)
      showNotification(err.message || 'Failed to auto-apply', 'error')
    } finally {
      setIsAutoApplying(false)
      setActiveJobIdAutoApplying(null)
    }
  }

  const handleToggleBulkId = (jobId: string) => {
    setBulkTailorIds((prev) => {
      const next = new Set(prev)
      if (next.has(jobId)) {
        next.delete(jobId)
      } else {
        next.add(jobId)
      }
      return next
    })
  }

  const handleTrack = async (job: JobListing, newStatus: string) => {
    const oldStatus = job.tracker_status
    try {
      await updateTrackerStatus(job.id, newStatus)
      const trackerData = await fetchTracker()
      setApplications(trackerData.applications || [])
      setJobs((prev) =>
        prev.map((j) => (j.id === job.id ? { ...j, tracker_status: newStatus } : j))
      )
      showNotification(
        `Moved ${job.title} to "${newStatus}"`,
        'success',
        oldStatus
          ? () => {
              updateTrackerStatus(job.id, oldStatus).then(() => {
                fetchTracker().then((td) => setApplications(td.applications || []))
                setJobs((prev) =>
                  prev.map((j) => (j.id === job.id ? { ...j, tracker_status: oldStatus } : j))
                )
              })
            }
          : undefined
      )
    } catch (err) {
      console.error('Track error:', err)
    }
  }

  const handleUpdateTrackerStatus = async (jobId: string, newStatus: string, notes?: string) => {
    try {
      await updateTrackerStatus(jobId, newStatus, notes)
      const trackerData = await fetchTracker()
      setApplications(trackerData.applications || [])
    } catch (err) {
      console.error('Update tracker error:', err)
    }
  }

  const handleDeleteTracker = async (jobId: string) => {
    try {
      await deleteTrackerJob(jobId)
      const trackerData = await fetchTracker()
      setApplications(trackerData.applications || [])
      setJobs((prev) =>
        prev.map((j) => (j.id === jobId ? { ...j, tracker_status: undefined } : j))
      )
    } catch (err) {
      console.error('Delete tracker error:', err)
    }
  }

  return (
    <div className={`min-h-screen ${darkMode ? 'bg-[#1a1a2e] text-slate-200' : 'bg-[#f4f2ee] text-slate-900'} flex flex-col selection:bg-[#0a66c2] selection:text-white`}>
      {/* Toast Notification */}
      {notification && (
        <div
          className={`fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-xl shadow-2xl text-xs font-semibold border flex items-center gap-2 animate-in slide-in-from-bottom duration-200 ${
            notification.type === 'error'
              ? 'bg-rose-950/90 border-rose-500/40 text-rose-200'
              : 'bg-emerald-950/90 border-emerald-500/40 text-emerald-200'
          }`}
        >
          <span>{notification.message}</span>
          {notification.undoAction && (
            <button
              onClick={() => {
                notification.undoAction?.()
                setNotification(null)
              }}
              className="ml-2 px-2 py-0.5 rounded-full bg-white/20 hover:bg-white/30 text-white text-[10px] font-bold cursor-pointer transition-colors"
            >
              Undo
            </button>
          )}
        </div>
      )}

      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenScan={() => setIsScanningModalOpen(true)}
        isScanning={isScanning}
        totalJobs={jobs.length}
        darkMode={darkMode}
        onToggleDark={() => setDarkMode((d) => !d)}
      />

      {/* Main Tab View */}
      <main className="flex-1 overflow-hidden">
        {activeTab === 'jobs' && (
          <JobSplitView
            jobs={jobs}
            selectedJob={selectedJob}
            onSelectJob={handleSelectJob}
            onTailor={handleTailor}
            onTrack={handleTrack}
            onAutoApply={handleAutoApply}
            isAutoApplying={isAutoApplying}
            activeJobIdAutoApplying={activeJobIdAutoApplying}
            tailoredOutput={tailoredOutput}
            isTailoring={isTailoring}
            activeJobIdTailoring={activeJobIdTailoring}
            bulkTailorIds={bulkTailorIds}
            onToggleBulkId={handleToggleBulkId}
            onBulkTailor={handleBulkTailor}
            darkMode={darkMode}
          />
        )}

        {activeTab === 'pipeline' && (
          <TrackerKanban
            applications={applications}
            onUpdateStatus={handleUpdateTrackerStatus}
            onDelete={handleDeleteTracker}
            onSelectJobForReview={(jobId) => {
              const found = jobs.find((j) => j.id === jobId)
              if (found) {
                setSelectedJob(found)
                setActiveTab('jobs')
              }
            }}
            darkMode={darkMode}
          />
        )}

        {activeTab === 'studio' && (
          <TailorStudio
            jobs={jobs}
            selectedJob={selectedJob}
            onSelectJob={handleSelectJob}
            tailoredOutput={tailoredOutput}
            onTailor={handleTailor}
            onAutoApply={handleAutoApply}
            isAutoApplying={isAutoApplying}
            activeJobIdAutoApplying={activeJobIdAutoApplying}
            isTailoring={isTailoring}
            darkMode={darkMode}
          />
        )}

        {activeTab === 'master_resume' && <MasterResumeView />}

        {activeTab === 'settings' && <SettingsView />}
      </main>

      {/* Autonomous ATS Scanner Modal */}
      <ScanModal
        isOpen={isScanningModalOpen}
        onClose={() => setIsScanningModalOpen(false)}
        onScanFinished={async () => {
          await loadInitialData()
          showNotification('Scan completed and job listings refreshed!')
        }}
      />
    </div>
  )
}

export default App
