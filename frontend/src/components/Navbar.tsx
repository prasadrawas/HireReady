import React from 'react'
import { Briefcase, CheckCircle2, Sliders, Play, Layers } from 'lucide-react'

interface NavbarProps {
  activeTab: 'jobs' | 'pipeline' | 'studio' | 'settings'
  setActiveTab: (tab: 'jobs' | 'pipeline' | 'studio' | 'settings') => void
  onOpenScan: () => void
  isScanning: boolean
  totalJobs: number
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  onOpenScan,
  isScanning,
  totalJobs,
}) => {
  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Briefcase className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="text-xl font-bold tracking-tight text-white flex items-center gap-1.5">
              Hire<span className="gradient-text">Ready</span>
            </span>
            <span className="text-xs text-slate-400 block -mt-1 font-medium">
              Autonomous ATS Job Scanner & Tailor
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 bg-slate-900/80 p-1.5 rounded-xl border border-slate-800/80">
          <button
            onClick={() => setActiveTab('jobs')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'jobs'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Briefcase className="w-4 h-4" />
            <span>Jobs</span>
            {totalJobs > 0 && (
              <span className="ml-1 text-xs px-1.5 py-0.2 rounded-full bg-slate-800 text-slate-300 font-semibold">
                {totalJobs}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('pipeline')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'pipeline'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Pipeline</span>
          </button>

          <button
            onClick={() => setActiveTab('studio')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'studio'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Tailor Studio</span>
          </button>

          <button
            onClick={() => setActiveTab('settings')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'settings'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Sliders className="w-4 h-4" />
            <span>Settings</span>
          </button>
        </nav>

        {/* Scan Action */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenScan}
            disabled={isScanning}
            className={`relative group overflow-hidden rounded-xl px-4 py-2 text-sm font-semibold transition-all duration-300 flex items-center gap-2 shadow-lg ${
              isScanning
                ? 'bg-amber-600/80 text-white animate-pulse'
                : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-blue-500/25 hover:shadow-blue-500/40'
            }`}
          >
            <Play className={`w-4 h-4 ${isScanning ? 'animate-spin' : ''}`} />
            <span>{isScanning ? 'Scanning...' : 'Scan ATS Boards'}</span>
          </button>
        </div>
      </div>
    </header>
  )
}
