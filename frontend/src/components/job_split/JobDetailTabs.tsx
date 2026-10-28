import React, { useState } from 'react'
import {
  Flag,
  Building2,
  CheckCircle2,
  GitCompare,
  FileText,
  ShieldCheck,
  Download,
  Copy,
  Check,
  AlertTriangle,
  Info,
} from 'lucide-react'
import { JobListing, JobOutput } from '../../types'
import {
  DetailTab,
  formatCheckName,
  getSeverityColor,
  getVerdictColor,
  parseAndFormatJD,
  parseDiffFromChangeSummary,
} from './helpers'

interface JobDetailTabsProps {
  activeTab: DetailTab
  setActiveTab: (tab: DetailTab) => void
  job: JobListing
  tailoredOutput: JobOutput | null
  onTailor: (job: JobListing, coverLetter: boolean) => Promise<void>
  darkMode: boolean
}

export const JobDetailTabs: React.FC<JobDetailTabsProps> = ({
  activeTab,
  setActiveTab,
  job,
  tailoredOutput,
  onTailor,
  darkMode,
}) => {
  const [copiedCoverLetter, setCopiedCoverLetter] = useState(false)

  const coverLetterText = tailoredOutput?.cover_letter_txt || tailoredOutput?.cover_letter

  const handleCopyCoverLetter = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedCoverLetter(true)
    setTimeout(() => setCopiedCoverLetter(false), 2000)
  }

  const tabsConfig = [
    { id: 'jd' as DetailTab, label: 'About the Job', show: true },
    {
      id: 'red_flags' as DetailTab,
      label: 'Red Flags',
      show: true,
      icon: <Flag className="w-3.5 h-3.5" />,
      count: tailoredOutput?.red_flags?.total,
    },
    {
      id: 'company' as DetailTab,
      label: 'Company',
      show: true,
      icon: <Building2 className="w-3.5 h-3.5" />,
    },
    {
      id: 'resume' as DetailTab,
      label: 'Tailored Resume',
      show: job.has_tailored_resume,
      icon: <CheckCircle2 className="w-3.5 h-3.5" />,
    },
    {
      id: 'diff' as DetailTab,
      label: 'Diff',
      show: job.has_tailored_resume && !!tailoredOutput?.change_summary,
      icon: <GitCompare className="w-3.5 h-3.5" />,
    },
    {
      id: 'cover_letter' as DetailTab,
      label: 'Cover Letter',
      show: job.has_tailored_resume,
      icon: <FileText className="w-3.5 h-3.5" />,
    },
    {
      id: 'validation' as DetailTab,
      label: 'ATS Report',
      show: job.has_tailored_resume,
      icon: <ShieldCheck className="w-3.5 h-3.5" />,
    },
  ]

  return (
    <div className="space-y-6">
      {/* Subtabs Bar */}
      <div
        className={`flex items-center gap-1 border-b pb-2 overflow-x-auto ${
          darkMode ? 'border-[#1e3a5f]' : 'border-slate-200'
        }`}
      >
        {tabsConfig
          .filter((t) => t.show)
          .map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-2 text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer whitespace-nowrap ${
                activeTab === tab.id
                  ? darkMode
                    ? 'bg-[#1e3a5f] text-[#0a66c2] border-b-2 border-b-[#0a66c2]'
                    : 'bg-slate-100 text-slate-900 border-b-2 border-b-slate-900'
                  : darkMode
                  ? 'text-slate-400 hover:text-slate-200'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              {tab.icon}
              {tab.label}
              {tab.count !== undefined && tab.count > 0 && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 font-bold">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
      </div>

      {/* TAB CONTENT: JD */}
      {activeTab === 'jd' && (
        <div className="space-y-4">
          <h3 className={`text-lg font-bold ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>About the job</h3>
          <div
            className="jd-content"
            dangerouslySetInnerHTML={{
              __html: parseAndFormatJD(job.description_html, job.description_text),
            }}
          />
        </div>
      )}

      {/* TAB CONTENT: RED FLAGS */}
      {activeTab === 'red_flags' && (
        <div className="space-y-4">
          <h3 className={`text-lg font-bold ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>Red Flag Analysis</h3>

          {tailoredOutput?.red_flags ? (
            <div className="space-y-4">
              <div className={`p-4 rounded-xl border flex items-center justify-between ${getVerdictColor(tailoredOutput.red_flags.verdict)}`}>
                <div className="flex items-center gap-3">
                  <Flag className="w-5 h-5" />
                  <div>
                    <p className="text-sm font-bold">Verdict: {tailoredOutput.red_flags.verdict.replace(/_/g, ' ')}</p>
                    <p className="text-xs mt-0.5">
                      {tailoredOutput.red_flags.total} total flags ({tailoredOutput.red_flags.critical} critical, {tailoredOutput.red_flags.warnings} warnings)
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                {tailoredOutput.red_flags.flags.map((flag, idx) => (
                  <div key={idx} className={`p-4 rounded-xl border ${getSeverityColor(flag.severity)}`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-bold uppercase tracking-wider">{flag.category}</span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getSeverityColor(flag.severity)}`}>
                        {flag.severity.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-sm font-semibold mb-1">{flag.signal}</p>
                    <p className="text-xs opacity-80">{flag.evidence}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className={`p-8 rounded-xl border text-center ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-slate-50 border-slate-200'}`}>
              <Flag className={`w-8 h-8 mx-auto mb-2 ${darkMode ? 'text-slate-500' : 'text-slate-300'}`} />
              <p className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                Red flag analysis will appear here after tailoring. Click "Tailor Resume" to generate.
              </p>
            </div>
          )}

          {job.red_flags && job.red_flags.length > 0 && !tailoredOutput?.red_flags && (
            <div className="space-y-2">
              <h4 className={`text-sm font-bold ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>Detected Concerns</h4>
              {job.red_flags.map((rf, i) => (
                <div key={i} className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-800 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  {rf}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: COMPANY BRIEF */}
      {activeTab === 'company' && (
        <div className="space-y-4">
          <h3 className={`text-lg font-bold ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>Company Research</h3>

          {tailoredOutput?.company_brief ? (
            <div className="space-y-4">
              <div className={`p-5 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
                <h4 className={`text-base font-bold ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>
                  {tailoredOutput.company_brief.company_name}
                </h4>
                <div className="flex flex-wrap gap-2 mt-2">
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 font-semibold">
                    {tailoredOutput.company_brief.industry}
                  </span>
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200 font-semibold">
                    {tailoredOutput.company_brief.stage}
                  </span>
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 font-semibold">
                    ~{tailoredOutput.company_brief.estimated_size} employees
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
                  <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Known For</h5>
                  <p className={`text-sm ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>{tailoredOutput.company_brief.known_for}</p>
                </div>
                <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
                  <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Funding</h5>
                  <p className={`text-sm ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>{tailoredOutput.company_brief.funding_status}</p>
                </div>
                <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
                  <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Glassdoor Sentiment</h5>
                  <p className={`text-sm ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>{tailoredOutput.company_brief.glassdoor_sentiment}</p>
                </div>
                <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
                  <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Verdict</h5>
                  <p className={`text-sm font-semibold ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>{tailoredOutput.company_brief.verdict}</p>
                </div>
              </div>

              {tailoredOutput.company_brief.tech_stack_signals.length > 0 && (
                <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
                  <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Tech Stack Signals</h5>
                  <div className="flex flex-wrap gap-1.5">
                    {tailoredOutput.company_brief.tech_stack_signals.map((t, i) => (
                      <span key={i} className="text-[11px] px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 font-medium">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {tailoredOutput.company_brief.culture_signals.length > 0 && (
                <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
                  <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Culture Signals</h5>
                  <div className="flex flex-wrap gap-1.5">
                    {tailoredOutput.company_brief.culture_signals.map((c, i) => (
                      <span key={i} className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {tailoredOutput.company_brief.notable_facts.length > 0 && (
                <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
                  <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Notable Facts</h5>
                  <ul className="space-y-1">
                    {tailoredOutput.company_brief.notable_facts.map((f, i) => (
                      <li key={i} className={`text-xs flex items-start gap-2 ${darkMode ? 'text-slate-200' : 'text-slate-700'}`}>
                        <Info className="w-3.5 h-3.5 text-blue-500 shrink-0 mt-0.5" />
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {tailoredOutput.company_brief.potential_concerns.length > 0 && (
                <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-amber-50 border-amber-200'}`}>
                  <h5 className="text-xs font-bold uppercase tracking-wider mb-2 text-amber-700">Potential Concerns</h5>
                  <ul className="space-y-1">
                    {tailoredOutput.company_brief.potential_concerns.map((c, i) => (
                      <li key={i} className="text-xs text-amber-800 flex items-start gap-2">
                        <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                        {c}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className={`p-8 rounded-xl border text-center ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-slate-50 border-slate-200'}`}>
              <Building2 className={`w-8 h-8 mx-auto mb-2 ${darkMode ? 'text-slate-500' : 'text-slate-300'}`} />
              <p className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                Company research will appear here after tailoring. Click "Tailor Resume" to generate.
              </p>
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: TAILORED RESUME */}
      {activeTab === 'resume' && (
        <div className="space-y-4">
          <div className={`flex items-center justify-between p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-slate-50 border-slate-200'}`}>
            <div>
              <h4 className={`text-sm font-bold ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>Custom Targeted Resume</h4>
              <p className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                Optimized for {job.company}'s ATS keyword filter with verified page fit.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <a
                href={`/api/jobs/${job.id}/pdf`}
                download={`Resume_${job.company}_${job.title}.pdf`}
                className="px-4 py-2 rounded-full bg-[#057642] hover:bg-[#046237] text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" /> Download PDF
              </a>
              <a
                href={`/api/jobs/${job.id}/html`}
                target="_blank"
                rel="noreferrer"
                className={`px-4 py-2 rounded-full border text-xs font-semibold cursor-pointer ${
                  darkMode ? 'border-[#1e3a5f] hover:bg-[#16213e] text-slate-300' : 'border-slate-300 hover:bg-white text-slate-700'
                }`}
              >
                Open HTML
              </a>
            </div>
          </div>

          <div className={`w-full h-[650px] rounded-xl overflow-hidden border shadow-xs ${darkMode ? 'border-[#2a4a6f] bg-[#1e3a5f]' : 'border-slate-200 bg-white'}`}>
            <iframe
              src={`/api/jobs/${job.id}/pdf`}
              className="w-full h-full"
              title="Tailored Resume Preview"
            />
          </div>
        </div>
      )}

      {/* TAB CONTENT: DIFF */}
      {activeTab === 'diff' && tailoredOutput?.change_summary && (
        <div className="space-y-4">
          <h3 className={`text-lg font-bold ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>Resume Changes Diff</h3>

          {(() => {
            const { removed, added, keywords } = parseDiffFromChangeSummary(tailoredOutput.change_summary || '')
            return (
              <div className="space-y-4">
                {keywords.length > 0 && (
                  <div className={`p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
                    <h5 className={`text-xs font-bold uppercase tracking-wider mb-2 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>Keywords Highlighted</h5>
                    <div className="flex flex-wrap gap-1.5">
                      {keywords.map((kw, i) => (
                        <span key={i} className="diff-keyword text-[11px] px-2 py-0.5 rounded-full">
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className={`rounded-xl border overflow-hidden ${darkMode ? 'border-[#2a4a6f]' : 'border-slate-200'}`}>
                  {removed.length > 0 && (
                    <div className="border-b border-slate-200">
                      <div className="px-4 py-2 bg-red-50 text-xs font-bold text-red-700 border-b border-red-200">Removed / Replaced</div>
                      <div className="p-4 space-y-1">
                        {removed.map((line, i) => (
                          <div key={i} className="diff-remove text-xs py-1 px-2 rounded">{line}</div>
                        ))}
                      </div>
                    </div>
                  )}
                  {added.length > 0 && (
                    <div>
                      <div className="px-4 py-2 bg-green-50 text-xs font-bold text-green-700 border-b border-green-200">Added / Updated</div>
                      <div className="p-4 space-y-1">
                        {added.map((line, i) => (
                          <div key={i} className="diff-add text-xs py-1 px-2 rounded">{line}</div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <details className={`rounded-xl border ${darkMode ? 'border-[#2a4a6f]' : 'border-slate-200'}`}>
                  <summary className={`px-4 py-3 text-xs font-semibold cursor-pointer ${darkMode ? 'text-slate-300' : 'text-slate-600'}`}>
                    View Raw Change Summary
                  </summary>
                  <div className={`px-4 pb-4 text-xs font-mono whitespace-pre-wrap leading-relaxed ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>
                    {tailoredOutput.change_summary}
                  </div>
                </details>
              </div>
            )
          })()}
        </div>
      )}

      {/* TAB CONTENT: COVER LETTER */}
      {activeTab === 'cover_letter' && (
        <div className="space-y-4">
          <div className={`flex items-center justify-between p-4 rounded-xl border ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-slate-50 border-slate-200'}`}>
            <div>
              <h4 className={`text-sm font-bold ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>Custom Cover Letter</h4>
              <p className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                Tailored addressing {job.company}'s specific challenges and team mission.
              </p>
            </div>
            {coverLetterText && (
              <button
                onClick={() => handleCopyCoverLetter(coverLetterText)}
                className="px-4 py-2 rounded-full bg-[#0a66c2] hover:bg-[#004182] text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
              >
                {copiedCoverLetter ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedCoverLetter ? 'Copied!' : 'Copy to Clipboard'}</span>
              </button>
            )}
          </div>

          <div
            className={`p-6 rounded-xl border whitespace-pre-line text-sm leading-relaxed font-serif shadow-xs ${
              darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f] text-slate-200' : 'bg-white border-slate-200 text-slate-800'
            }`}
          >
            {coverLetterText || (
              <div className={`text-center py-10 ${darkMode ? 'text-slate-400' : 'text-slate-400'}`}>
                <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No cover letter generated yet.</p>
                <button
                  onClick={() => onTailor(job, true)}
                  className="mt-3 px-4 py-1.5 rounded-full bg-[#0a66c2] text-white text-xs font-semibold cursor-pointer"
                >
                  Generate Cover Letter
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB CONTENT: ATS MATCH REPORT */}
      {activeTab === 'validation' && (
        <div className="space-y-4">
          <div className={`p-5 rounded-xl border space-y-4 ${darkMode ? 'bg-[#1e3a5f] border-[#2a4a6f]' : 'bg-white border-slate-200'}`}>
            <div className="flex items-center justify-between">
              <h4 className={`text-sm font-bold uppercase tracking-wider flex items-center gap-2 ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>
                <ShieldCheck className="w-4 h-4 text-[#057642]" /> Automated ATS Inspection
              </h4>
              {tailoredOutput?.validation_report && (
                <span
                  className={`text-xs font-bold px-3 py-1 rounded-full border ${
                    tailoredOutput.validation_report.passed
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-200 dark:border-emerald-800'
                      : 'bg-amber-50 text-amber-800 border-amber-300 dark:bg-amber-950 dark:text-amber-200 dark:border-amber-800'
                  }`}
                >
                  {tailoredOutput.validation_report.passed
                    ? `${tailoredOutput.validation_report.checks?.filter((c: any) => c.passed).length || 9} / ${tailoredOutput.validation_report.checks?.length || 9} Checks Passed`
                    : 'Needs Minor Review'}
                </span>
              )}
            </div>

            {tailoredOutput?.validation_report ? (
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  {tailoredOutput.validation_report.checks?.map((chk: any, idx: number) => {
                    const checkName = formatCheckName(chk.check, chk.name)
                    return (
                      <div
                        key={idx}
                        className={`p-3.5 rounded-xl border flex items-start gap-3 transition-all ${
                          darkMode ? 'bg-[#16213e] border-[#1e3a5f]' : 'bg-white border-slate-200 shadow-2xs hover:border-slate-300'
                        }`}
                      >
                        {chk.passed ? (
                          <div className="w-5 h-5 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0 mt-0.5 border border-emerald-200 dark:bg-emerald-950 dark:border-emerald-800 dark:text-emerald-300">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                          </div>
                        ) : (
                          <div className="w-5 h-5 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center shrink-0 mt-0.5 border border-amber-200 dark:bg-amber-950 dark:border-amber-800 dark:text-amber-300">
                            <AlertTriangle className="w-3.5 h-3.5" />
                          </div>
                        )}
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center justify-between gap-2">
                            <p className={`font-semibold text-xs leading-tight ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>
                              {checkName}
                            </p>
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                                chk.passed
                                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800'
                                  : 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800'
                              }`}
                            >
                              {chk.passed ? 'PASSED' : 'CHECK'}
                            </span>
                          </div>
                          {chk.detail && (
                            <p className={`text-[11px] mt-1 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                              {chk.detail}
                            </p>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            ) : (
              <p className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>Validation report not yet generated.</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

