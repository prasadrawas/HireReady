import React, { useState, useEffect } from 'react'
import { Navbar } from './components/Navbar'
import { JobSplitView } from './components/JobSplitView'
import { TrackerKanban } from './components/TrackerKanban'
import { TailorStudio } from './components/TailorStudio'
import { SettingsView } from './components/SettingsView'
import { ScanModal } from './components/ScanModal'
import {
  fetchJobs,
  fetchStats,
  fetchTracker,
  fetchJobOutput,
  tailorJob,
  updateTrackerStatus,
  deleteTrackerJob,
} from './api'
import { JobListing, JobOutput, TrackerApplication } from './types'

export function App() {
  const [activeTab, setActiveTab] = useState<'jobs' | 'pipeline' | 'studio' | 'settings'>('jobs')
  const [jobs, setJobs] = useState<JobListing[]>([])
  const [applications, setApplications] = useState<TrackerApplication[]>([])
  const [selectedJob, setSelectedJob] = useState<JobListing | null>(null)
  const [tailoredOutput, setTailoredOutput] = useState<JobOutput | null>(null)
  const [isScanningModalOpen, setIsScanningModalOpen] = useState(false)
  const [isScanning, setIsScanning] = useState(false)
  const [isTailoring, setIsTailoring] = useState(false)
  const [activeJobIdTailoring, setActiveJobIdTailoring] = useState<string | null>(null)
  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

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

  const showNotification = (message: string, type: 'success' | 'error' = 'success') => {
    setNotification({ message, type })
    setTimeout(() => setNotification(null), 3500)
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

      showNotification(`Tailored resume & assets created for ${job.company}!`)
    } catch (err: any) {
      console.error('Tailor error:', err)
      showNotification(err.message || 'Failed to tailor resume', 'error')
    } finally {
      setIsTailoring(false)
      setActiveJobIdTailoring(null)
    }
  }

  const handleTrack = async (job: JobListing, newStatus: string) => {
    try {
      await updateTrackerStatus(job.id, newStatus)
      const trackerData = await fetchTracker()
      setApplications(trackerData.applications || [])
      setJobs((prev) =>
        prev.map((j) => (j.id === job.id ? { ...j, tracker_status: newStatus } : j))
      )
      showNotification(`Moved ${job.title} to "${newStatus}"`)
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
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col selection:bg-blue-600 selection:text-white">
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
        </div>
      )}

      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenScan={() => setIsScanningModalOpen(true)}
        isScanning={isScanning}
        totalJobs={jobs.length}
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
            tailoredOutput={tailoredOutput}
            isTailoring={isTailoring}
            activeJobIdTailoring={activeJobIdTailoring}
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
          />
        )}

        {activeTab === 'studio' && (
          <TailorStudio
            jobs={jobs}
            selectedJob={selectedJob}
            onSelectJob={handleSelectJob}
            tailoredOutput={tailoredOutput}
            onTailor={handleTailor}
            isTailoring={isTailoring}
          />
        )}

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
