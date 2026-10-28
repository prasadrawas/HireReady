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
    <div className="p-6 max-w-5xl mx-auto space-y-8 pb-12 overflow-y-auto h-[calc(100vh-4rem)]">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
          <Sliders className="w-5 h-5 text-blue-500" /> Scanner Preferences & ATS Sources
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Customize what the autonomous scraper looks for and manage company career portals.
        </p>
      </div>

      {/* Preferences Section */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h3 className="text-base font-bold text-white">Job Search Criteria</h3>
            <p className="text-xs text-slate-400">
              Corresponds to <code className="text-blue-400">input/preferences.yaml</code>
            </p>
          </div>
          <button
            onClick={handleSavePreferences}
            disabled={isSaving}
            className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-blue-600/30 transition-all"
          >
            {saveSuccess ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-300" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            <span>{isSaving ? 'Saving...' : saveSuccess ? 'Saved!' : 'Save Preferences'}</span>
          </button>
        </div>

        {/* Target Roles */}
        <div className="space-y-2">
          <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">
            Target Roles
          </label>
          <div className="flex flex-wrap gap-2 mb-2">
            {(preferences.target_roles || []).map((role: string, i: number) => (
              <span
                key={i}
                className="px-3 py-1 rounded-lg bg-blue-500/15 text-blue-300 border border-blue-500/30 text-xs font-medium flex items-center gap-1.5"
              >
                <span>{role}</span>
                <button
                  onClick={() => removeTag('target_roles', i)}
                  className="hover:text-red-400 font-bold"
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
              placeholder="Add role (e.g. Senior Backend Engineer)..."
              className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button
              onClick={() => addTag('target_roles', newRoleInput, setNewRoleInput)}
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
            >
              Add
            </button>
          </div>
        </div>

        {/* Target Keywords */}
        <div className="space-y-2">
          <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">
            Target Keywords
          </label>
          <div className="flex flex-wrap gap-2 mb-2">
            {(preferences.target_keywords || []).map((kw: string, i: number) => (
              <span
                key={i}
                className="px-3 py-1 rounded-lg bg-purple-500/15 text-purple-300 border border-purple-500/30 text-xs font-medium flex items-center gap-1.5"
              >
                <span>{kw}</span>
                <button
                  onClick={() => removeTag('target_keywords', i)}
                  className="hover:text-red-400 font-bold"
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
              placeholder="Add keyword (e.g. Python, Spark, React)..."
              className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-purple-500"
            />
            <button
              onClick={() => addTag('target_keywords', newKeywordInput, setNewKeywordInput)}
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
            >
              Add
            </button>
          </div>
        </div>

        {/* Locations & Remote Toggle */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              Locations
            </label>
            <div className="flex flex-wrap gap-2 mb-2">
              {(preferences.locations || []).map((loc: string, i: number) => (
                <span
                  key={i}
                  className="px-3 py-1 rounded-lg bg-slate-800 text-slate-300 border border-slate-700 text-xs font-medium flex items-center gap-1.5"
                >
                  <span>{loc}</span>
                  <button
                    onClick={() => removeTag('locations', i)}
                    className="hover:text-red-400 font-bold"
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
                placeholder="Add location (e.g. Remote, San Francisco)..."
                className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <button
                onClick={() => addTag('locations', newLocationInput, setNewLocationInput)}
                className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
              >
                Add
              </button>
            </div>
          </div>

          <div className="space-y-3 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
              Preferences Options
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={preferences.remote_only || false}
                onChange={(e) => setPreferences({ ...preferences, remote_only: e.target.checked })}
                className="w-4 h-4 rounded bg-slate-800 border-slate-700 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-xs font-medium text-slate-300">
                Strict Remote Only (Filter out non-remote listings)
              </span>
            </label>
          </div>
        </div>
      </div>

      {/* ATS Companies Manager */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-6">
        <div className="border-b border-slate-800 pb-4">
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Building className="w-5 h-5 text-indigo-400" /> Configured ATS Companies
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Automatically scrapes public career boards on Lever, Greenhouse, Ashby, Workable, SmartRecruiters, etc.
          </p>
        </div>

        {/* Add ATS Link input */}
        <div className="space-y-2">
          <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
            Add Company ATS Link (Auto-detects Platform & Slug)
          </label>
          <div className="flex gap-2 max-w-xl">
            <div className="relative flex-1">
              <LinkIcon className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={newUrl}
                onChange={(e) => setNewUrl(e.target.value)}
                placeholder="https://jobs.ashbyhq.com/ramp or https://boards.greenhouse.io/airbnb"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-9 pr-4 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
            <button
              onClick={handleAddLink}
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-indigo-600/30 transition-all shrink-0"
            >
              <Plus className="w-3.5 h-3.5" /> Add Board
            </button>
          </div>
          {linkError && (
            <p className="text-xs text-rose-400 flex items-center gap-1 mt-1">
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
                className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 space-y-2"
              >
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                    {platform}
                  </span>
                  <span className="text-xs font-bold text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full border border-blue-500/20">
                    {list.length}
                  </span>
                </div>
                <div className="max-h-40 overflow-y-auto space-y-1.5 pr-1">
                  {list.map((slug: string) => (
                    <div
                      key={slug}
                      className="flex items-center justify-between text-xs py-1 px-2 rounded-lg bg-slate-950/60 border border-slate-800/80 group"
                    >
                      <span className="text-slate-300 font-mono truncate max-w-[180px]">{slug}</span>
                      <button
                        onClick={() => handleDeleteLink(platform, slug)}
                        className="text-slate-500 hover:text-rose-400 p-0.5 opacity-60 group-hover:opacity-100 transition-opacity"
                        title="Remove Company"
                      >
                        <Trash2 className="w-3 h-3" />
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
  )
}
