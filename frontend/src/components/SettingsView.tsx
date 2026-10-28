import React, { useState, useEffect } from 'react'
import {
  Save,
  Plus,
  Trash2,
  Sliders,
  Link as LinkIcon,
  CheckCircle2,
  AlertCircle,
  Building,
} from 'lucide-react'
import {
  fetchPreferences,
  savePreferences,
  fetchAtsLinks,
  addAtsLink,
  deleteAtsLink,
} from '../api'

export const SettingsView: React.FC = () => {
  const [preferences, setPreferences] = useState<any>({
    target_roles: [],
    target_keywords: [],
    locations: [],
    remote_only: false,
    min_seniority: 'senior',
  })
  const [atsConfig, setAtsConfig] = useState<Record<string, any>>({})
  const [newUrl, setNewUrl] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [newRoleInput, setNewRoleInput] = useState('')
  const [newKeywordInput, setNewKeywordInput] = useState('')
  const [newLocationInput, setNewLocationInput] = useState('')
  const [linkError, setLinkError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [prefs, ats] = await Promise.all([fetchPreferences(), fetchAtsLinks()])
      setPreferences(prefs)
      setAtsConfig(ats)
    } catch (err) {
      console.error('Error loading settings:', err)
    }
  }

  const handleSavePreferences = async () => {
    setIsSaving(true)
    try {
      await savePreferences(preferences)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 2500)
    } catch (err) {
      console.error('Failed to save preferences:', err)
    } finally {
      setIsSaving(false)
    }
  }

  const handleAddLink = async () => {
    if (!newUrl.trim()) return
    setLinkError(null)
    try {
      const updated = await addAtsLink({ url: newUrl.trim() })
      setAtsConfig(updated.data || updated)
      setNewUrl('')
    } catch (err: any) {
      setLinkError(err.message || 'Failed to add link')
    }
  }

  const handleDeleteLink = async (platform: string, slug: string) => {
    try {
      const updated = await deleteAtsLink(platform, slug)
      setAtsConfig(updated.data || updated)
    } catch (err) {
      console.error('Failed to delete ATS link:', err)
    }
  }

  const addTag = (field: string, val: string, setInput: (v: string) => void) => {
    if (!val.trim()) return
    const current = preferences[field] || []
    if (!current.includes(val.trim())) {
      setPreferences({ ...preferences, [field]: [...current, val.trim()] })
    }
    setInput('')
  }

  const removeTag = (field: string, index: number) => {
    const current = [...(preferences[field] || [])]
    current.splice(index, 1)
    setPreferences({ ...preferences, [field]: current })
  }

  return (
    <div className="bg-[#f4f2ee] h-[calc(100vh-3.5rem)] overflow-y-auto p-4 sm:p-6 pb-16">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header Bar */}
        <div className="bg-white p-5 sm:p-6 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-[#edf3f8] text-[#0a66c2]">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                Scanner Preferences & ATS Portals
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Customize autonomous scraper keywords, title matching, and company career board sources.
              </p>
            </div>
          </div>

          <button
            onClick={handleSavePreferences}
            disabled={isSaving}
            className="px-5 py-2 rounded-full bg-[#0a66c2] hover:bg-[#004182] text-white text-xs font-bold flex items-center gap-2 shadow-xs transition-all cursor-pointer disabled:opacity-50"
          >
            {saveSuccess ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-200" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            <span>{isSaving ? 'Saving...' : saveSuccess ? 'Preferences Saved!' : 'Save Preferences'}</span>
          </button>
        </div>

        {/* Preferences Section */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-6">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-base font-bold text-slate-900">Job Matching Criteria</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Syncs with <code className="text-[#0a66c2] bg-blue-50 px-1 py-0.5 rounded font-mono text-[11px]">input/preferences.yaml</code>
            </p>
          </div>

          {/* Target Roles */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
              Target Job Titles
            </label>
            <div className="flex flex-wrap gap-2 mb-2">
              {(preferences.target_roles || []).map((role: string, i: number) => (
                <span
                  key={i}
                  className="px-3 py-1 rounded-full bg-[#edf3f8] text-[#0a66c2] border border-[#d0e2f5] text-xs font-semibold flex items-center gap-1.5"
                >
                  <span>{role}</span>
                  <button
                    onClick={() => removeTag('target_roles', i)}
                    className="hover:text-red-600 font-bold ml-0.5 cursor-pointer"
                  >
                    &times;
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2 max-w-md">
              <input
                type="text"
                value={newRoleInput}
                onChange={(e) => setNewRoleInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addTag('target_roles', newRoleInput, setNewRoleInput)}
                placeholder="Add title (e.g. Senior Software Engineer)..."
                className="flex-1 bg-white border border-slate-300 focus:border-[#0a66c2] focus:ring-1 focus:ring-[#0a66c2] rounded-lg px-3 py-1.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none"
              />
              <button
                onClick={() => addTag('target_roles', newRoleInput, setNewRoleInput)}
                className="px-3.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold cursor-pointer"
              >
                Add
              </button>
            </div>
          </div>

          {/* Target Keywords */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
              Core Skills & Keywords
            </label>
            <div className="flex flex-wrap gap-2 mb-2">
              {(preferences.target_keywords || []).map((kw: string, i: number) => (
                <span
                  key={i}
                  className="px-3 py-1 rounded-full bg-purple-50 text-purple-700 border border-purple-200 text-xs font-semibold flex items-center gap-1.5"
                >
                  <span>{kw}</span>
                  <button
                    onClick={() => removeTag('target_keywords', i)}
                    className="hover:text-red-600 font-bold ml-0.5 cursor-pointer"
                  >
                    &times;
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2 max-w-md">
              <input
                type="text"
                value={newKeywordInput}
                onChange={(e) => setNewKeywordInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addTag('target_keywords', newKeywordInput, setNewKeywordInput)}
                placeholder="Add keyword (e.g. Python, Distributed Systems, React)..."
                className="flex-1 bg-white border border-slate-300 focus:border-[#0a66c2] focus:ring-1 focus:ring-[#0a66c2] rounded-lg px-3 py-1.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none"
              />
              <button
                onClick={() => addTag('target_keywords', newKeywordInput, setNewKeywordInput)}
                className="px-3.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold cursor-pointer"
              >
                Add
              </button>
            </div>
          </div>

          {/* Locations & Remote Toggle */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
                Target Locations
              </label>
              <div className="flex flex-wrap gap-2 mb-2">
                {(preferences.locations || []).map((loc: string, i: number) => (
                  <span
                    key={i}
                    className="px-3 py-1 rounded-full bg-slate-100 text-slate-700 border border-slate-200 text-xs font-semibold flex items-center gap-1.5"
                  >
                    <span>{loc}</span>
                    <button
                      onClick={() => removeTag('locations', i)}
                      className="hover:text-red-600 font-bold ml-0.5 cursor-pointer"
                    >
                      &times;
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newLocationInput}
                  onChange={(e) => setNewLocationInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && addTag('locations', newLocationInput, setNewLocationInput)}
                  placeholder="Add location (e.g. Remote, United States, San Francisco)..."
                  className="flex-1 bg-white border border-slate-300 focus:border-[#0a66c2] focus:ring-1 focus:ring-[#0a66c2] rounded-lg px-3 py-1.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none"
                />
                <button
                  onClick={() => addTag('locations', newLocationInput, setNewLocationInput)}
                  className="px-3.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold cursor-pointer"
                >
                  Add
                </button>
              </div>
            </div>

            <div className="space-y-3 bg-[#f8fafc] p-4 rounded-xl border border-slate-200">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
                Workplace Filter
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={preferences.remote_only || false}
                  onChange={(e) => setPreferences({ ...preferences, remote_only: e.target.checked })}
                  className="w-4 h-4 rounded text-[#0a66c2] focus:ring-[#0a66c2] border-slate-300"
                />
                <span className="text-xs font-medium text-slate-800">
                  Strict Remote Only (Exclude non-remote postings)
                </span>
              </label>
            </div>
          </div>
        </div>

        {/* ATS Companies Manager */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-6">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Building className="w-5 h-5 text-[#0a66c2]" /> Configured ATS Company Portals
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Autonomous scraper monitors public career endpoints across Greenhouse, Lever, Ashby, Workable, SmartRecruiters, etc.
            </p>
          </div>

          {/* Add ATS Link input */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
              Add Company ATS Link (Auto-detects Platform & Slug)
            </label>
            <div className="flex gap-2 max-w-xl">
              <div className="relative flex-1">
                <LinkIcon className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={newUrl}
                  onChange={(e) => setNewUrl(e.target.value)}
                  placeholder="e.g. https://jobs.ashbyhq.com/ramp or https://boards.greenhouse.io/airbnb"
                  className="w-full bg-white border border-slate-300 focus:border-[#0a66c2] focus:ring-1 focus:ring-[#0a66c2] rounded-lg pl-9 pr-4 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none"
                />
              </div>
              <button
                onClick={handleAddLink}
                className="px-5 py-2 rounded-full bg-[#0a66c2] hover:bg-[#004182] text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all shrink-0 cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" /> Add Board
              </button>
            </div>
            {linkError && (
              <p className="text-xs text-rose-600 flex items-center gap-1 mt-1">
                <AlertCircle className="w-3.5 h-3.5" /> {linkError}
              </p>
            )}
          </div>

          {/* ATS Companies Grid by Platform */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
            {Object.entries(atsConfig).map(([platform, data]) => {
              const list = Array.isArray(data) ? data : data.companies || []
              if (list.length === 0) return null

              return (
                <div
                  key={platform}
                  className="bg-[#f8fafc] p-4 rounded-xl border border-slate-200 space-y-2 shadow-2xs"
                >
                  <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-800">
                      {platform}
                    </span>
                    <span className="text-xs font-bold text-[#0a66c2] bg-[#edf3f8] px-2 py-0.5 rounded-full border border-[#d0e2f5]">
                      {list.length} boards
                    </span>
                  </div>
                  <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                    {list.map((slug: string) => (
                      <div
                        key={slug}
                        className="flex items-center justify-between text-xs py-1.5 px-2.5 rounded-lg bg-white border border-slate-200 shadow-2xs group"
                      >
                        <span className="text-slate-700 font-mono font-medium truncate max-w-[180px]">
                          {slug}
                        </span>
                        <button
                          onClick={() => handleDeleteLink(platform, slug)}
                          className="text-slate-400 hover:text-rose-600 p-0.5 opacity-60 group-hover:opacity-100 transition-opacity cursor-pointer"
                          title="Remove Company"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
