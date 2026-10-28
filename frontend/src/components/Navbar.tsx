import React from 'react'
import { Briefcase, CheckCircle2, Sliders, Play, Layers, Sun, Moon } from 'lucide-react'

interface NavbarProps {
  activeTab: 'jobs' | 'pipeline' | 'studio' | 'settings'
  setActiveTab: (tab: 'jobs' | 'pipeline' | 'studio' | 'settings') => void
  onOpenScan: () => void
  isScanning: boolean
  totalJobs: number
  darkMode: boolean
  onToggleDark: () => void
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  onOpenScan,
  isScanning,
  totalJobs,
  darkMode,
  onToggleDark,
}) => {
  return (
    <header className={`sticky top-0 z-40 w-full border-b shadow-xs ${darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#0a66c2] flex items-center justify-center shadow-xs">
            <Briefcase className="w-4 h-4 text-white" />
          </div>
          <div>
            <span className={`text-lg font-bold tracking-tight flex items-center gap-1 ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>
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
                ? `border-${darkMode ? '[#0a66c2]' : 'slate-900'} ${darkMode ? 'text-[#0a66c2]' : 'text-slate-900'}`
                : `border-transparent ${darkMode ? 'text-slate-400 hover:text-slate-200' : 'text-slate-500 hover:text-slate-800'}`
            }`}
          >
            <div className="flex items-center gap-1.5">
              <Briefcase className="w-4 h-4" />
              <span>Jobs</span>
              {totalJobs > 0 && (
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold border ${darkMode ? 'bg-[#1e3a5f] text-slate-300 border-[#2a4a6f]' : 'bg-slate-100 text-slate-700 border-slate-200'}`}>
                  {totalJobs}
                </span>
              )}
            </div>
          </button>

          <button
            onClick={() => setActiveTab('pipeline')}
            className={`flex flex-col items-center justify-center h-14 px-3 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
              activeTab === 'pipeline'
                ? `border-${darkMode ? '[#0a66c2]' : 'slate-900'} ${darkMode ? 'text-[#0a66c2]' : 'text-slate-900'}`
                : `border-transparent ${darkMode ? 'text-slate-400 hover:text-slate-200' : 'text-slate-500 hover:text-slate-800'}`
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
                ? `border-${darkMode ? '[#0a66c2]' : 'slate-900'} ${darkMode ? 'text-[#0a66c2]' : 'text-slate-900'}`
                : `border-transparent ${darkMode ? 'text-slate-400 hover:text-slate-200' : 'text-slate-500 hover:text-slate-800'}`
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
                ? `border-${darkMode ? '[#0a66c2]' : 'slate-900'} ${darkMode ? 'text-[#0a66c2]' : 'text-slate-900'}`
                : `border-transparent ${darkMode ? 'text-slate-400 hover:text-slate-200' : 'text-slate-500 hover:text-slate-800'}`
            }`}
          >
            <div className="flex items-center gap-1.5">
              <Sliders className="w-4 h-4" />
              <span>Preferences & ATS</span>
            </div>
          </button>
        </nav>

        {/* Scan Action + Dark Mode Toggle */}
        <div className="flex items-center gap-2">
          <button
            onClick={onToggleDark}
            className={`p-2 rounded-full transition-all cursor-pointer ${darkMode ? 'hover:bg-[#1e3a5f] text-amber-400' : 'hover:bg-slate-100 text-slate-500'}`}
            title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

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
