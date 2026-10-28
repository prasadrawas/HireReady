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
    <header className="sticky top-0 z-40 w-full bg-white border-b border-slate-200 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#0a66c2] flex items-center justify-center shadow-xs">
            <Briefcase className="w-4 h-4 text-white" />
          </div>
          <div>
            <span className="text-lg font-bold tracking-tight text-slate-900 flex items-center gap-1">
              Hire<span className="text-[#0a66c2]">Ready</span>
            </span>
          </div>
        </div>

        {/* Navigation Tabs (LinkedIn Style) */}
        <nav className="flex items-center h-full gap-1 sm:gap-6">
          <button
            onClick={() => setActiveTab('jobs')}
            className={`flex flex-col items-center justify-center h-14 px-3 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
              activeTab === 'jobs'
                ? 'border-slate-900 text-slate-900'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <div className="flex items-center gap-1.5">
              <Briefcase className="w-4 h-4" />
              <span>Jobs</span>
              {totalJobs > 0 && (
                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-100 text-slate-700 font-bold border border-slate-200">
                  {totalJobs}
                </span>
              )}
            </div>
          </button>

          <button
            onClick={() => setActiveTab('pipeline')}
            className={`flex flex-col items-center justify-center h-14 px-3 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
              activeTab === 'pipeline'
                ? 'border-slate-900 text-slate-900'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <div className="flex items-center gap-1.5">
              <Layers className="w-4 h-4" />
              <span>My Jobs / Pipeline</span>
            </div>
          </button>

          <button
            onClick={() => setActiveTab('studio')}
            className={`flex flex-col items-center justify-center h-14 px-3 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
              activeTab === 'studio'
                ? 'border-slate-900 text-slate-900'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" />
              <span>Tailor Studio</span>
            </div>
          </button>

          <button
            onClick={() => setActiveTab('settings')}
            className={`flex flex-col items-center justify-center h-14 px-3 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
              activeTab === 'settings'
                ? 'border-slate-900 text-slate-900'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <div className="flex items-center gap-1.5">
              <Sliders className="w-4 h-4" />
              <span>Preferences & ATS</span>
            </div>
          </button>
        </nav>

        {/* Scan Action */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenScan}
            disabled={isScanning}
            className={`rounded-full px-4 py-1.5 text-xs font-semibold transition-all duration-200 flex items-center gap-1.5 shadow-xs cursor-pointer ${
              isScanning
                ? 'bg-amber-600 text-white animate-pulse'
                : 'bg-[#0a66c2] hover:bg-[#004182] text-white'
            }`}
          >
            <Play className={`w-3.5 h-3.5 fill-current ${isScanning ? 'animate-spin' : ''}`} />
            <span>{isScanning ? 'Scanning...' : 'Scan ATS Boards'}</span>
          </button>
        </div>
      </div>
    </header>
  )
}
