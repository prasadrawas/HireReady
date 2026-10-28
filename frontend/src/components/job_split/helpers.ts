export type DetailTab = 'jd' | 'red_flags' | 'company' | 'resume' | 'diff' | 'cover_letter' | 'validation'

export function getDaysAgo(dateStr?: string): string | null {
  if (!dateStr) return null
  try {
    const posted = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - posted.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return '1 day ago'
    if (diffDays < 7) return `${diffDays} days ago`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`
    return `${Math.floor(diffDays / 30)}mo ago`
  } catch {
    return null
  }
}

export function parseDiffFromChangeSummary(changeSummary: string): { removed: string[]; added: string[]; keywords: string[] } {
  const removed: string[] = []
  const added: string[] = []
  const keywords: string[] = []

  const lines = changeSummary.split('\n')
  for (const line of lines) {
    const trimmed = line.trim()
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const content = trimmed.slice(2).trim()
      if (content.toLowerCase().includes('removed') || content.toLowerCase().includes('replaced') || content.toLowerCase().includes('original')) {
        removed.push(content)
      } else if (content.toLowerCase().includes('added') || content.toLowerCase().includes('new') || content.toLowerCase().includes('tailored') || content.toLowerCase().includes('updated')) {
        added.push(content)
      } else {
        added.push(content)
      }
    }

    const keywordMatches = trimmed.match(/`([^`]+)`/g) || []
    for (const kw of keywordMatches) {
      keywords.push(kw.replace(/`/g, ''))
    }
    const boldMatches = trimmed.match(/\*\*([^*]+)\*\*/g) || []
    for (const bm of boldMatches) {
      keywords.push(bm.replace(/\*\*/g, ''))
    }
  }

  return { removed, added, keywords: [...new Set(keywords)] }
}

const CHECK_TITLES: Record<string, string> = {
  pdf_opens: 'PDF Opens Successfully',
  text_extractable: 'Machine-Readable Text Layer',
  section_headings_intact: 'Standard ATS Section Headings',
  contact_info_present: 'Contact & Header Info Verified',
  keyword_verification: 'Targeted ATS Keyword Density',
  no_unsupported_claims: 'Master Resume Fact Integrity',
  page_count: 'Page Count Within Guidelines',
  no_garbled_text: 'Clean Typography & UTF-8 Encoding',
  html_pdf_consistency: 'Visual & Textual Consistency',
}

export function formatCheckName(checkKey?: string, name?: string): string {
  if (name && name.trim()) return name
  if (!checkKey) return 'Automated Verification Check'
  if (CHECK_TITLES[checkKey]) return CHECK_TITLES[checkKey]
  return checkKey
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

export function getSeverityColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case 'critical':
    case 'high':
      return 'bg-rose-50 border-rose-300 text-rose-800 dark:bg-rose-950 dark:border-rose-800 dark:text-rose-200'
    case 'medium':
    case 'warning':
      return 'bg-amber-50 border-amber-300 text-amber-800 dark:bg-amber-950 dark:border-amber-800 dark:text-amber-200'
    case 'low':
    case 'info':
      return 'bg-blue-50 border-blue-300 text-blue-700 dark:bg-blue-950 dark:border-blue-800 dark:text-blue-200'
    default:
      return 'bg-indigo-50 border-indigo-200 text-indigo-700 dark:bg-indigo-950 dark:border-indigo-800 dark:text-indigo-200'
  }
}

export function getVerdictColor(verdict: string): string {
  switch (verdict.toLowerCase()) {
    case 'clean':
      return 'bg-emerald-50 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-200 dark:border-emerald-800'
    case 'mostly_clean':
      return 'bg-emerald-50 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-200 dark:border-emerald-800'
    case 'minor_concerns':
      return 'bg-amber-50 text-amber-800 border-amber-300 dark:bg-amber-950 dark:text-amber-200 dark:border-amber-800'
    case 'proceed_with_caution':
      return 'bg-orange-50 text-orange-800 border-orange-300 dark:bg-orange-950 dark:text-orange-200 dark:border-orange-800'
    case 'avoid':
      return 'bg-rose-50 text-rose-800 border-rose-300 dark:bg-rose-950 dark:text-rose-200 dark:border-rose-800'
    default:
      return 'bg-blue-50 text-blue-800 border-blue-200 dark:bg-blue-950 dark:text-blue-200 dark:border-blue-800'
  }
}

export function parseAndFormatJD(rawHtml?: string, rawText?: string): string {
  if (!rawHtml && !rawText) return '<p class="text-slate-500">No description provided.</p>'

  let str = rawHtml || rawText || ''

  let maxPasses = 5
  while (maxPasses-- > 0 && (str.includes('&lt;') || str.includes('&amp;') || str.includes('&#'))) {
    const textarea = document.createElement('textarea')
    textarea.innerHTML = str
    const decoded = textarea.value
    if (decoded === str) break
    str = decoded
  }

  if (!rawHtml && rawText && !str.includes('<p>') && !str.includes('<div>')) {
    str = str
      .split('\n\n')
      .map(p => `<p class="mb-3">${p.replace(/\n/g, '<br/>')}</p>`)
      .join('')
  }

  str = str.replace(/\s*style\s*=\s*"[^"]*"/gi, '')
  str = str.replace(/\s*style\s*=\s*'[^']*'/gi, '')

  return str
}

