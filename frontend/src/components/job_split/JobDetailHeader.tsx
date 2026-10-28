import React, { useState } from 'react'
import { ExternalLink, Bot, Check, Link, Sparkles, FileText } from 'lucide-react'
import { JobListing } from '../../types'
import { CompanyLogo } from '../CompanyLogo'
import { getDaysAgo, getVerdictColor } from './helpers'

interface JobDetailHeaderProps {
  job: JobListing
  onAutoApply?: (job: JobListing, autoSubmit?: boolean) => Promise<void>
  isAutoApplying?: boolean
  activeJobIdAutoApplying?: string | null
  onTailor: (job: JobListing, coverLetter: boolean) => Promise<void>
  isTailoring: boolean
  activeJobIdTailoring?: string | null
  onTrack: (job: JobListing, status: string) => void
  darkMode: boolean
}

export const JobDetailHeader: React.FC<JobDetailHeaderProps> = ({
  job,
  onAutoApply,
  isAutoApplying,
  activeJobIdAutoApplying,
  onTailor,
  isTailoring,
  activeJobIdTailoring,
  onTrack,
  darkMode,
}) => {
  const [copiedUrl, setCopiedUrl] = useState(false)

  const handleCopyUrl = (url: string) => {
    navigator.clipboard.writeText(url)
    setCopiedUrl(true)
    setTimeout(() => setCopiedUrl(false), 2000)
  }

  const daysAgo = getDaysAgo(job.posted_date)
  const isSalaryNotListed = !job.salary || job.salary.toLowerCase().includes('not listed')

  return (
    <div className={`p-6 border-b shrink-0 ${darkMode ? 'border-[#1e3a5f] bg-[#16213e]' : 'border-slate-200 bg-white'}`}>
      <div className="flex items-start gap-4">
        <CompanyLogo
          company={job.company}
          companySlug={job.company_slug}
          className="w-14 h-14 rounded-xl text-lg shrink-0 shadow-xs"
        />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`text-sm font-bold ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>{job.company}</span>
            <span className={darkMode ? 'text-slate-600' : 'text-slate-300'}>&bull;</span>
            <span className="text-[11px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800">
              {job.ats_source}
            </span>
            {job.remote && (
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-300 dark:bg-emerald-950 dark:text-emerald-200 dark:border-emerald-800">
                Remote
              </span>
            )}
            {daysAgo && (
              <>
                <span className={darkMode ? 'text-slate-600' : 'text-slate-300'}>&bull;</span>
                <span className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>{daysAgo}</span>
              </>
            )}
          </div>

          <h1 className={`text-2xl font-bold tracking-tight mt-1 leading-snug ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>
            {job.title}
          </h1>

          <p className={`text-xs mt-1 font-medium ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
            {job.location || 'Location unlisted'}
            {job.team && ` · ${job.team}`}
            {job.workplace_type && ` · ${job.workplace_type.charAt(0).toUpperCase() + job.workplace_type.slice(1)}`}
            {job.employment_type && ` · ${job.employment_type.replace(/_/g, ' ')}`}
          </p>
        </div>
      </div>

      {/* Pill Row */}
      <div className="flex flex-wrap items-center gap-2 mt-4 text-xs">
        {job.salary && (
          isSalaryNotListed ? (
            <span className="px-3 py-1 rounded-full font-medium bg-amber-50 text-amber-800 border border-amber-200 dark:bg-amber-950 dark:text-amber-200 dark:border-amber-800">
              Salary: Not listed
            </span>
          ) : (
            <span className="px-3 py-1 rounded-full font-semibold bg-emerald-50 text-emerald-800 border border-emerald-300 dark:bg-emerald-950 dark:text-emerald-200 dark:border-emerald-800">
              {job.salary}
            </span>
          )
        )}

        {job.red_flag_verdict && (
          <span className={`px-3 py-1 rounded-full font-semibold border capitalize ${getVerdictColor(job.red_flag_verdict)}`}>
            {job.red_flag_verdict.replace(/_/g, ' ')}
          </span>
        )}

        {job.has_equity && (
          <span className="px-3 py-1 rounded-full bg-amber-50 text-amber-900 font-semibold border border-amber-300 dark:bg-amber-950 dark:text-amber-200 dark:border-amber-800">
            ★ Offers Equity
          </span>
        )}

        {job.locations && job.locations.length > 1 && (
          <span
            className="px-3 py-1 rounded-full font-medium bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-950 dark:text-indigo-200 dark:border-indigo-800"
            title={job.locations.join(', ')}
          >
            +{job.locations.length - 1} more locations
          </span>
        )}
      </div>

      {/* Primary Button Row — height decreased by 10-12px (30px) */}
      <div className="flex flex-wrap items-center gap-2 mt-4 pt-2">
        {/* 1. Apply */}
        <a
          href={job.application_url}
          target="_blank"
          rel="noopener noreferrer"
          className="h-[30px] px-4 rounded-full bg-[#0a66c2] hover:bg-[#004182] text-white text-xs font-semibold inline-flex items-center justify-center gap-1.5 shadow-xs transition-all cursor-pointer"
        >
          <span>Apply</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </a>

        {/* 2. Auto-Apply */}
        {onAutoApply && (
          <button
            onClick={() => onAutoApply(job, false)}
            disabled={isAutoApplying && activeJobIdAutoApplying === job.id}
            className="h-[30px] px-4 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold inline-flex items-center justify-center gap-1.5 shadow-xs transition-all cursor-pointer disabled:opacity-60"
            title="Auto-fill form, upload resume & cover letter, and answer custom questions via Playwright"
          >
            {isAutoApplying && activeJobIdAutoApplying === job.id ? (
              <>
                <span className="animate-spin text-xs">⟳</span>
                <span>Auto-Applying...</span>
              </>
            ) : (
              <>
                <Bot className="w-3.5 h-3.5" />
                <span>Auto-Apply</span>
              </>
            )}
          </button>
        )}

        {/* 3. Stage / Save */}
        <button
          onClick={() => onTrack(job, job.tracker_status === 'saved' ? 'applied' : 'saved')}
          className={`h-[30px] px-4 rounded-full text-xs font-semibold inline-flex items-center justify-center gap-1.5 transition-all cursor-pointer border ${
            job.tracker_status
              ? 'border-blue-300 dark:border-blue-700 bg-blue-50 hover:bg-blue-100 dark:bg-blue-950 dark:hover:bg-blue-900 text-[#0a66c2] dark:text-blue-300'
              : darkMode
              ? 'border-[#2a4a6f] bg-[#1e3a5f] hover:bg-[#25466f] text-slate-200'
              : 'border-slate-300 bg-white hover:bg-slate-50 text-slate-700'
          }`}
        >
          {job.tracker_status ? `Stage: ${job.tracker_status}` : 'Save'}
        </button>

        {/* 4. Tailor Resume / Re-Tailor */}
        <button
          onClick={() => onTailor(job, false)}
          disabled={isTailoring && activeJobIdTailoring === job.id}
          className="h-[30px] px-4 rounded-full bg-violet-600 hover:bg-violet-700 text-white text-xs font-semibold inline-flex items-center justify-center gap-1.5 shadow-xs transition-all cursor-pointer disabled:opacity-50"
        >
          {isTailoring && activeJobIdTailoring === job.id ? (
            <span className="animate-spin text-xs">⟳</span>
          ) : (
            <Sparkles className="w-3.5 h-3.5" />
          )}
          <span>{job.has_tailored_resume ? 'Re-Tailor' : 'Tailor Resume'}</span>
        </button>

        {/* 5. Cover Letter */}
        <button
          onClick={() => onTailor(job, true)}
          disabled={isTailoring && activeJobIdTailoring === job.id}
          className={`h-[30px] px-4 rounded-full border text-xs font-semibold inline-flex items-center justify-center gap-1.5 shadow-2xs transition-all cursor-pointer ${
            darkMode
              ? 'border-[#2a4a6f] bg-[#1e3a5f] hover:bg-[#25466f] text-slate-200'
              : 'border-slate-300 bg-white hover:bg-slate-50 text-slate-700'
          }`}
        >
          <FileText className={`w-3.5 h-3.5 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`} />
          <span>Cover Letter</span>
        </button>

        {/* 6. Copy URL (At the END of the row) */}
        <button
          onClick={() => handleCopyUrl(job.application_url)}
          className={`h-[30px] w-[30px] rounded-full border inline-flex items-center justify-center transition-all cursor-pointer shrink-0 shadow-2xs ${
            copiedUrl
              ? 'border-emerald-400 bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-700'
              : darkMode
              ? 'border-[#2a4a6f] bg-[#1e3a5f] hover:bg-[#25466f] text-slate-400 hover:text-slate-200'
              : 'border-slate-300 bg-white hover:bg-slate-50 text-slate-500 hover:text-slate-700'
          }`}
          title="Copy application URL"
        >
          {copiedUrl ? <Check className="w-3.5 h-3.5" /> : <Link className="w-3.5 h-3.5" />}
        </button>
      </div>
    </div>
  )
}

