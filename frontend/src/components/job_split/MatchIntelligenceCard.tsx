import React from 'react'
import { Sparkles } from 'lucide-react'
import { JobListing } from '../../types'

interface MatchIntelligenceCardProps {
  job: JobListing
  onShowValidation: () => void
  onTailorResume: () => void
}

export const MatchIntelligenceCard: React.FC<MatchIntelligenceCardProps> = ({
  job,
  onShowValidation,
  onTailorResume,
}) => {
  const matchPercent = Math.round((job.score || 0.5) * 100)

  return (
    <div className="bg-[#fffbf2] border border-[#f5dfb8] rounded-xl p-4 sm:p-5 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-xs bg-[#c37d16] flex items-center justify-center text-[10px] text-white font-bold">
            in
          </span>
          <span className="text-xs font-bold text-[#b27800] uppercase tracking-wider">
            Premium Match Intelligence
          </span>
        </div>

        <span className="text-xs font-bold text-slate-700">
          Match Confidence: <span className="text-[#0a66c2]">{matchPercent}%</span>
        </span>
      </div>

      <div>
        <h4 className="text-base font-bold text-slate-900">
          Job match is{' '}
          <span className="text-[#0a66c2]">
            {matchPercent >= 70 ? 'high' : matchPercent >= 50 ? 'medium' : 'moderate'}
          </span>
          , review match details
        </h4>
        <p className="text-xs text-slate-600 mt-1">
          Your profile and resume match several of the key requirements for this position.
        </p>
      </div>

      {job.role_fit && (
        <div className="bg-white/80 p-3 rounded-lg border border-[#f5dfb8] text-xs text-slate-700 italic">
          "{job.role_fit}"
        </div>
      )}

      {/* Sub Action Pills */}
      <div className="flex flex-wrap items-center gap-2 pt-1">
        <button
          onClick={onShowValidation}
          className="px-3.5 py-1.5 rounded-full bg-white hover:bg-slate-50 border border-slate-300 text-xs font-semibold text-slate-800 flex items-center gap-1.5 cursor-pointer shadow-2xs"
        >
          <Sparkles className="w-3.5 h-3.5 text-[#c37d16]" />
          <span>Show match details</span>
        </button>

        <button
          onClick={onTailorResume}
          className="px-3.5 py-1.5 rounded-full bg-white hover:bg-slate-50 border border-slate-300 text-xs font-semibold text-slate-800 flex items-center gap-1.5 cursor-pointer shadow-2xs"
        >
          <Sparkles className="w-3.5 h-3.5 text-[#c37d16]" />
          <span>Tailor my resume</span>
        </button>

        {job.key_gaps && job.key_gaps.length > 0 && (
          <span className="text-xs text-slate-500 font-medium ml-1">
            {job.key_gaps.length} skill gaps detected
          </span>
        )}
      </div>

      {/* Missing Keywords */}
      {job.key_gaps && job.key_gaps.length > 0 && (
        <div className="pt-2 border-t border-[#f5dfb8]/60 flex flex-wrap gap-1.5">
          {job.key_gaps.map((gap, i) => (
            <span
              key={i}
              className="text-[11px] bg-amber-100/60 text-amber-900 border border-amber-300/60 px-2 py-0.5 rounded-full font-medium"
            >
              + {gap}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

