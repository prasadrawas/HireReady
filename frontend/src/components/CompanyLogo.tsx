import React, { useState } from 'react'

interface CompanyLogoProps {
  company: string
  companySlug?: string
  className?: string
}

const KNOWN_DOMAINS: Record<string, string> = {
  linear: 'linear.app',
  cal: 'cal.com',
  dbt: 'getdbt.com',
  'dbt-labs': 'getdbt.com',
  highlight: 'highlight.io',
  primer: 'primer.io',
  voiceflow: 'voiceflow.com',
  rewatch: 'rewatch.com',
  lottiefiles: 'lottiefiles.com',
  usercentrics: 'usercentrics.com',
  uber: 'uber.com',
  airbnb: 'airbnb.com',
  spotify: 'spotify.com',
  stripe: 'stripe.com',
  netflix: 'netflix.com',
  figma: 'figma.com',
  ramp: 'ramp.com',
  vercel: 'vercel.com',
  cloudflare: 'cloudflare.com',
  gitlab: 'gitlab.com',
  rippling: 'rippling.com',
}

const AVATAR_COLORS = [
  'bg-blue-600',
  'bg-indigo-600',
  'bg-purple-600',
  'bg-rose-600',
  'bg-amber-600',
  'bg-emerald-600',
  'bg-teal-600',
  'bg-cyan-600',
  'bg-violet-600',
  'bg-pink-600',
]

function getAvatarColor(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

function resolveDomain(company: string, slug?: string): string {
  const key = (slug || company).toLowerCase().trim().replace(/[^a-z0-9-]/g, '')
  if (KNOWN_DOMAINS[key]) {
    return KNOWN_DOMAINS[key]
  }

  // If slug has hyphens (e.g. attentive-mobile -> attentive.com)
  const primarySlug = slug ? slug.split('-')[0].toLowerCase() : ''
  if (primarySlug && KNOWN_DOMAINS[primarySlug]) {
    return KNOWN_DOMAINS[primarySlug]
  }

  // Remove common corporate suffixes
  const clean = company
    .toLowerCase()
    .replace(/\b(inc|corp|corporation|group|technologies|technology|tech|llc|ltd)\b/gi, '')
    .trim()
    .replace(/[^a-z0-9]/g, '')

  return slug ? `${slug.toLowerCase().replace(/[^a-z0-9-]/g, '')}.com` : `${clean || 'company'}.com`
}

export const CompanyLogo: React.FC<CompanyLogoProps> = ({
  company,
  companySlug,
  className = 'w-12 h-12 rounded-lg text-sm',
}) => {
  const [error, setError] = useState(false)
  const domain = resolveDomain(company, companySlug)
  const logoUrl = `https://www.google.com/s2/favicons?domain=${domain}&sz=128`
  const initials = company ? company.substring(0, 2).toUpperCase() : '??'
  const bgColor = getAvatarColor(company || 'Company')

  if (error) {
    return (
      <div
        className={`${className} ${bgColor} flex items-center justify-center text-white font-bold shrink-0 shadow-xs select-none`}
      >
        {initials}
      </div>
    )
  }

  return (
    <div
      className={`${className} bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center p-1.5 shrink-0 shadow-xs overflow-hidden select-none`}
    >
      <img
        src={logoUrl}
        alt={company}
        loading="lazy"
        className="w-full h-full object-contain"
        onError={() => setError(true)}
      />
    </div>
  )
}
