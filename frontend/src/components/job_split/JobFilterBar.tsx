import React from 'react'
import { Search, Sparkles } from 'lucide-react'

interface JobFilterBarProps {
  searchQuery: string
  setSearchQuery: (val: string) => void
  postedWithin: number
  setPostedWithin: (val: number) => void
  minScoreFilter: number
  setMinScoreFilter: (val: number) => void
  remoteOnly: boolean
  setRemoteOnly: (val: boolean | ((prev: boolean) => boolean)) => void
  selectedCompany: string
  setSelectedCompany: (val: string) => void
  availableCompanies: string[]
  selectedPlatform: string
  setSelectedPlatform: (val: string) => void
  availablePlatforms: string[]
  minSalaryFilter: number
  setMinSalaryFilter: (val: number) => void
  tailoredOnly: boolean
  setTailoredOnly: (val: boolean | ((prev: boolean) => boolean)) => void
  isBulkMode: boolean
  setIsBulkMode: (val: boolean | ((prev: boolean) => boolean)) => void
  darkMode: boolean
  hasActiveFilters: boolean
  onClearFilters: () => void
}

export const JobFilterBar: React.FC<JobFilterBarProps> = ({
  searchQuery,
  setSearchQuery,
  postedWithin,
  setPostedWithin,
  minScoreFilter,
  setMinScoreFilter,
  remoteOnly,
  setRemoteOnly,
  selectedCompany,
  setSelectedCompany,
  availableCompanies,
  selectedPlatform,
  setSelectedPlatform,
  availablePlatforms,
  minSalaryFilter,
  setMinSalaryFilter,
  tailoredOnly,
  setTailoredOnly,
  isBulkMode,
  setIsBulkMode,
  darkMode,
  hasActiveFilters,
  onClearFilters,
}) => {
  return (
    <div className={`border-b shrink-0 shadow-xs ${darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200'}`}>
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-5 py-2.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 flex-1">
          {/* Search Input */}
          <div className="relative min-w-[220px] max-w-xs">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by title, skill, or company"
              className={`w-full border border-transparent rounded-full pl-9 pr-4 py-1.5 text-xs placeholder-slate-500 focus:outline-none transition-all ${
                darkMode
                  ? 'bg-[#1e3a5f] hover:bg-[#243f63] focus:bg-[#1a1a2e] focus:border-[#0a66c2] text-slate-200'
                  : 'bg-[#edf3f8] hover:bg-[#e4ebf2] focus:bg-white focus:border-[#0a66c2] text-slate-900'
              }`}
            />
          </div>

          {/* 1. Posted Within */}
          <select
            value={postedWithin}
            onChange={(e) => setPostedWithin(parseInt(e.target.value))}
            className={`rounded-full px-3.5 py-1.5 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-[#0a66c2] cursor-pointer border ${
              darkMode
                ? 'bg-[#16213e] hover:bg-[#1e3a5f] text-slate-300 border-[#1e3a5f]'
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            <option value={0}>Date: Any time</option>
            <option value={1}>Today</option>
            <option value={3}>Last 3 days</option>
            <option value={7}>This week</option>
            <option value={14}>Past 2 weeks</option>
            <option value={30}>Past month</option>
          </select>

          {/* 2. Minimum Match Score */}
          <select
            value={minScoreFilter}
            onChange={(e) => setMinScoreFilter(parseFloat(e.target.value))}
            className={`rounded-full px-3.5 py-1.5 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-[#0a66c2] cursor-pointer border ${
              minScoreFilter > 0
                ? 'bg-[#0a66c2] text-white border-[#0a66c2]'
                : darkMode
                ? 'bg-[#16213e] hover:bg-[#1e3a5f] text-slate-300 border-[#1e3a5f]'
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            <option value={0}>Match: Any score</option>
            <option value={0.8}>High (80%+)</option>
            <option value={0.65}>Good (65%+)</option>
            <option value={0.5}>Moderate (50%+)</option>
          </select>

          {/* 3. Remote Only */}
          <button
            onClick={() => setRemoteOnly((p) => !p)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer ${
              remoteOnly
                ? 'bg-[#0a66c2] text-white border-[#0a66c2]'
                : darkMode
                ? 'bg-[#16213e] hover:bg-[#1e3a5f] text-slate-300 border-[#1e3a5f]'
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            Remote
          </button>

          {/* 4. Company */}
          <select
            value={selectedCompany}
            onChange={(e) => setSelectedCompany(e.target.value)}
            className={`rounded-full px-3.5 py-1.5 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-[#0a66c2] cursor-pointer border ${
              selectedCompany !== 'all'
                ? 'bg-[#0a66c2] text-white border-[#0a66c2]'
                : darkMode
                ? 'bg-[#16213e] hover:bg-[#1e3a5f] text-slate-300 border-[#1e3a5f]'
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            <option value="all">Company: All</option>
            {availableCompanies.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>

          {/* 5. ATS Source */}
          <select
            value={selectedPlatform}
            onChange={(e) => setSelectedPlatform(e.target.value)}
            className={`rounded-full px-3.5 py-1.5 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-[#0a66c2] cursor-pointer border ${
              selectedPlatform !== 'all'
                ? 'bg-[#0a66c2] text-white border-[#0a66c2]'
                : darkMode
                ? 'bg-[#16213e] hover:bg-[#1e3a5f] text-slate-300 border-[#1e3a5f]'
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            <option value="all">ATS: All</option>
            {availablePlatforms.map((p) => (
              <option key={p} value={p}>
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </option>
            ))}
          </select>

          {/* 6. Minimum Salary */}
          <select
            value={minSalaryFilter}
            onChange={(e) => setMinSalaryFilter(parseInt(e.target.value))}
            className={`rounded-full px-3.5 py-1.5 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-[#0a66c2] cursor-pointer border ${
              minSalaryFilter > 0
                ? 'bg-[#0a66c2] text-white border-[#0a66c2]'
                : darkMode
                ? 'bg-[#16213e] hover:bg-[#1e3a5f] text-slate-300 border-[#1e3a5f]'
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            <option value={0}>Salary: Any</option>
            <option value={100}>$100k+</option>
            <option value={150}>$150k+</option>
            <option value={180}>$180k+</option>
            <option value={200}>$200k+</option>
          </select>

          {/* 7. Tailored Only */}
          <button
            onClick={() => setTailoredOnly((p) => !p)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer ${
              tailoredOnly
                ? 'bg-purple-700 text-white border-purple-700'
                : darkMode
                ? 'bg-[#16213e] hover:bg-[#1e3a5f] text-slate-300 border-[#1e3a5f]'
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            Tailored
          </button>

          {/* Reset Filters */}
          {hasActiveFilters && (
            <button
              onClick={onClearFilters}
              className="text-xs text-red-600 hover:text-red-700 font-semibold px-2 cursor-pointer"
            >
              Clear filters
            </button>
          )}
        </div>

        {/* Bulk Action Toggle */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsBulkMode((p) => !p)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-bold border transition-all flex items-center gap-1.5 cursor-pointer ${
              isBulkMode
                ? 'bg-purple-700 text-white border-purple-700'
                : darkMode
                ? 'bg-[#16213e] hover:bg-[#1e3a5f] text-slate-300 border-[#1e3a5f]'
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{isBulkMode ? 'Done Bulk Select' : 'Bulk Customize'}</span>
          </button>
        </div>
      </div>
    </div>
  )
}

