import React, { useState, useEffect } from 'react'
import {
  FileText,
  Download,
  ExternalLink,
  ShieldCheck,
  Building2,
  Calendar,
  MapPin,
  Mail,
  Phone,
  Linkedin,
  Github,
  Globe,
  Award,
  GraduationCap,
  Briefcase,
  Layers,
  Sparkles,
  Search,
  CheckCircle2,
  Printer,
  Eye,
  ListTree,
} from 'lucide-react'
import { MasterResumeData } from '../types'
import { fetchMasterResumeData } from '../api'

export const MasterResumeView: React.FC = () => {
  const [data, setData] = useState<MasterResumeData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'preview' | 'structured'>('preview')
  const [skillSearch, setSkillSearch] = useState('')

  useEffect(() => {
    loadMasterResume()
  }, [])

  const loadMasterResume = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchMasterResumeData()
      setData(res.resume)
    } catch (err: any) {
      console.error('Failed to load master resume:', err)
      setError(err.message || 'Failed to load master resume.')
    } finally {
      setLoading(false)
    }
  }

  // Filter skills based on search
  const filteredSkills = data?.skills
    ?.map((group) => {
      if (!skillSearch) return group
      const matchingSkills = group.skills.filter((s) =>
        s.toLowerCase().includes(skillSearch.toLowerCase())
      )
      if (
        group.category.toLowerCase().includes(skillSearch.toLowerCase()) ||
        matchingSkills.length > 0
      ) {
        return {
          ...group,
          skills: matchingSkills.length > 0 ? matchingSkills : group.skills,
        }
      }
      return null
    })
    .filter(Boolean) as MasterResumeData['skills'] | undefined

  return (
    <div className="bg-[#f4f2ee] h-[calc(100vh-3.5rem)] overflow-y-auto flex flex-col">
      <div className="max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-5 flex-1 flex flex-col">
        {/* Top Header Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-wrap items-center justify-between gap-4 shrink-0">
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-xl bg-[#0a66c2] text-white flex items-center justify-center font-bold text-lg shadow-xs">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold text-slate-900 tracking-tight">Master Resume</h2>
                <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 text-[#057642] border border-emerald-200 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" />
                  Single Source of Truth
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Stored at <code className="text-[#0a66c2] bg-blue-50 px-1 py-0.5 rounded font-mono text-[11px]">input/master_resume.html</code> &bull; Immutable master profile used to tailor targeted resumes.
              </p>
            </div>
          </div>

          {/* Action Buttons & View Toggles */}
          <div className="flex flex-wrap items-center gap-2.5">
            {/* View Mode Toggle */}
            <div className="bg-[#edf3f8] p-1 rounded-full flex items-center border border-slate-200">
              <button
                onClick={() => setViewMode('preview')}
                className={`px-3.5 py-1.5 rounded-full text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                  viewMode === 'preview'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Visual Document</span>
              </button>
              <button
                onClick={() => setViewMode('structured')}
                className={`px-3.5 py-1.5 rounded-full text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                  viewMode === 'structured'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <ListTree className="w-3.5 h-3.5" />
                <span>Structured Data</span>
              </button>
            </div>

            {/* External Links */}
            <a
              href="/api/resume/master/html"
              target="_blank"
              rel="noreferrer"
              className="px-3.5 py-2 rounded-full border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-colors"
              title="Open full page HTML resume in a new tab"
            >
              <ExternalLink className="w-3.5 h-3.5 text-slate-500" />
              <span>Open in Tab</span>
            </a>

            <a
              href="/api/resume/master/pdf"
              download="master_resume.pdf"
              className="px-4 py-2 rounded-full bg-[#0a66c2] hover:bg-[#004182] text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download PDF</span>
            </a>
          </div>
        </div>

        {/* Candidate Identity Quick Strip */}
        {data && (
          <div className="bg-white rounded-xl border border-slate-200 px-5 py-3 shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs shrink-0">
            <div className="flex flex-wrap items-center gap-4">
              <span className="font-bold text-slate-900 text-sm">{data.contact.name}</span>
              {data.contact.email && (
                <span className="flex items-center gap-1 text-slate-600">
                  <Mail className="w-3.5 h-3.5 text-slate-400" />
                  {data.contact.email}
                </span>
              )}
              {data.contact.phone && (
                <span className="flex items-center gap-1 text-slate-600">
                  <Phone className="w-3.5 h-3.5 text-slate-400" />
                  {data.contact.phone}
                </span>
              )}
              {data.contact.location && (
                <span className="flex items-center gap-1 text-slate-600">
                  <MapPin className="w-3.5 h-3.5 text-slate-400" />
                  {data.contact.location}
                </span>
              )}
            </div>

            <div className="flex items-center gap-3">
              {data.contact.linkedin && (
                <a
                  href={data.contact.linkedin}
                  target="_blank"
                  rel="noreferrer"
                  className="text-slate-500 hover:text-[#0a66c2] flex items-center gap-1"
                >
                  <Linkedin className="w-3.5 h-3.5 text-[#0a66c2]" /> LinkedIn
                </a>
              )}
              {data.contact.github && (
                <a
                  href={data.contact.github}
                  target="_blank"
                  rel="noreferrer"
                  className="text-slate-500 hover:text-slate-900 flex items-center gap-1"
                >
                  <Github className="w-3.5 h-3.5" /> GitHub
                </a>
              )}
              {data.contact.website && (
                <a
                  href={data.contact.website}
                  target="_blank"
                  rel="noreferrer"
                  className="text-slate-500 hover:text-emerald-700 flex items-center gap-1"
                >
                  <Globe className="w-3.5 h-3.5 text-emerald-600" /> Portfolio
                </a>
              )}
            </div>
          </div>
        )}

        {/* View Content Area */}
        <div className="flex-1 overflow-hidden">
          {viewMode === 'preview' ? (
            /* =========================================================================
               MODE 1: Visual Document Preview (Embedded HTML iframe)
               ========================================================================= */
            <div className="w-full h-full min-h-[700px] rounded-xl overflow-hidden border border-slate-200 bg-white shadow-xs flex flex-col">
              <iframe
                src="/api/resume/master/html"
                className="w-full h-full flex-1 border-0"
                title="Master Resume Preview"
              />
            </div>
          ) : (
            /* =========================================================================
               MODE 2: Structured Data View
               ========================================================================= */
            <div className="h-full overflow-y-auto space-y-5 pr-1 pb-10">
              {/* Executive Summary */}
              {data?.summary && (
                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-2">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-[#0a66c2]" />
                    Executive Summary
                  </h3>
                  <p className="text-sm text-slate-800 leading-relaxed font-sans">{data.summary}</p>
                </div>
              )}

              {/* Skills Section with Filter */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-[#0a66c2]" />
                    Core Competencies & Skills ({data?.skills?.reduce((acc, g) => acc + g.skills.length, 0) || 0})
                  </h3>
                  <div className="relative min-w-[200px]">
                    <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={skillSearch}
                      onChange={(e) => setSkillSearch(e.target.value)}
                      placeholder="Filter skills..."
                      className="w-full bg-[#edf3f8] border border-transparent focus:border-[#0a66c2] focus:bg-white rounded-full pl-8 pr-3 py-1 text-xs text-slate-900 focus:outline-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filteredSkills?.map((group, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-xl bg-[#f8fafc] border border-slate-200 space-y-2 shadow-2xs"
                    >
                      <h4 className="text-xs font-bold text-slate-900">{group.category}</h4>
                      <div className="flex flex-wrap gap-1.5">
                        {group.skills.map((skill, sIdx) => (
                          <span
                            key={sIdx}
                            className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-white border border-slate-200 text-slate-800 shadow-2xs"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Professional Experience with Bullet Point IDs */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-5">
                <div className="border-b border-slate-100 pb-3">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                    <Briefcase className="w-3.5 h-3.5 text-[#0a66c2]" />
                    Professional Experience ({data?.experience?.length || 0})
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Each bullet carries a deterministic ID used by HireReady to guarantee 100% evidence-backed tailoring without fabrication.
                  </p>
                </div>

                <div className="space-y-6">
                  {data?.experience?.map((exp, expIdx) => (
                    <div
                      key={expIdx}
                      className="p-5 rounded-xl bg-[#f8fafc] border border-slate-200 space-y-3"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <h4 className="text-sm font-bold text-slate-900">{exp.title}</h4>
                          <p className="text-xs font-semibold text-[#0a66c2] flex items-center gap-1 mt-0.5">
                            <Building2 className="w-3 h-3" />
                            {exp.company}
                          </p>
                        </div>
                        <div className="text-right text-xs text-slate-500 font-medium">
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3 text-slate-400" />
                            {exp.start_date} &ndash; {exp.end_date || 'Present'}
                          </span>
                          {exp.location && (
                            <span className="flex items-center gap-1 mt-0.5 text-slate-400">
                              <MapPin className="w-3 h-3" />
                              {exp.location}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Bullets with deterministic IDs */}
                      <ul className="space-y-2 pt-2">
                        {exp.bullets.map((b) => (
                          <li key={b.id} className="flex items-start gap-2 text-xs text-slate-700 leading-relaxed">
                            <span className="font-mono text-[10px] text-[#0a66c2] bg-blue-50 px-1.5 py-0.5 rounded border border-blue-200 shrink-0 select-all font-semibold" title="Evidence ID">
                              {b.id}
                            </span>
                            <span className="pt-0.5">{b.text}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>

              {/* Notable Projects */}
              {data?.projects && data.projects.length > 0 && (
                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
                  <div className="border-b border-slate-100 pb-3">
                    <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-[#0a66c2]" />
                      Featured Projects ({data.projects.length})
                    </h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {data.projects.map((proj, pIdx) => (
                      <div
                        key={pIdx}
                        className="p-4 rounded-xl bg-[#f8fafc] border border-slate-200 space-y-2.5 flex flex-col justify-between"
                      >
                        <div>
                          <div className="flex items-center justify-between gap-2">
                            <h4 className="text-sm font-bold text-slate-900">{proj.name}</h4>
                            {proj.url && (
                              <a
                                href={proj.url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-slate-400 hover:text-[#0a66c2]"
                              >
                                <ExternalLink className="w-3.5 h-3.5" />
                              </a>
                            )}
                          </div>
                          {proj.description && (
                            <p className="text-xs text-slate-600 mt-1">{proj.description}</p>
                          )}
                          {proj.bullets && proj.bullets.length > 0 && (
                            <ul className="space-y-1.5 mt-2">
                              {proj.bullets.map((b) => (
                                <li key={b.id} className="text-xs text-slate-700 flex items-start gap-1.5">
                                  <span className="text-slate-400">&bull;</span>
                                  <span>{b.text}</span>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>

                        {proj.technologies && proj.technologies.length > 0 && (
                          <div className="flex flex-wrap gap-1 pt-2 border-t border-slate-200/60">
                            {proj.technologies.map((t, tIdx) => (
                              <span
                                key={tIdx}
                                className="px-2 py-0.5 rounded text-[10px] font-semibold bg-white border border-slate-200 text-slate-700"
                              >
                                {t}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Education & Certifications */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {/* Education */}
                {data?.education && data.education.length > 0 && (
                  <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
                    <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5 border-b border-slate-100 pb-3">
                      <GraduationCap className="w-4 h-4 text-[#0a66c2]" />
                      Education
                    </h3>
                    <div className="space-y-3">
                      {data.education.map((edu, eIdx) => (
                        <div key={eIdx} className="p-3.5 rounded-xl bg-[#f8fafc] border border-slate-200">
                          <h4 className="text-xs font-bold text-slate-900">{edu.degree} {edu.field && `in ${edu.field}`}</h4>
                          <p className="text-xs text-[#0a66c2] font-semibold mt-0.5">{edu.institution}</p>
                          {(edu.start_date || edu.end_date) && (
                            <p className="text-[11px] text-slate-400 mt-1">
                              {edu.start_date} &ndash; {edu.end_date}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Certifications */}
                {data?.certifications && data.certifications.length > 0 && (
                  <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
                    <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5 border-b border-slate-100 pb-3">
                      <Award className="w-4 h-4 text-purple-700" />
                      Certifications
                    </h3>
                    <div className="space-y-2">
                      {data.certifications.map((cert, cIdx) => (
                        <div
                          key={cIdx}
                          className="p-3 rounded-xl bg-[#f8fafc] border border-slate-200 flex items-center gap-2 text-xs font-semibold text-slate-800"
                        >
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                          <span>{cert}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
