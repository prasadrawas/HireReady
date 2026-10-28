import React, { useEffect, useState, useRef } from 'react'
import { Terminal, CheckCircle2, AlertTriangle, X, Play, Loader2 } from 'lucide-react'

interface ScanModalProps {
  isOpen: boolean
  onClose: () => void
  onScanFinished: () => void
}

export const ScanModal: React.FC<ScanModalProps> = ({ isOpen, onClose, onScanFinished }) => {
  const [logs, setLogs] = useState<string[]>([])
  const [isScanning, setIsScanning] = useState(false)
  const [isCompleted, setIsCompleted] = useState(false)
  const [platformStats, setPlatformStats] = useState<Record<string, number>>({})
  const [summary, setSummary] = useState<{ total?: number; matched?: number; newCount?: number } | null>(null)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const startScan = () => {
    setLogs(['[SYSTEM] Initializing scan stream connection...'])
    setIsScanning(true)
    setIsCompleted(false)
    setPlatformStats({})
    setSummary(null)

    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    const es = new EventSource('/api/scan/stream')
    eventSourceRef.current = es

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'status') {
          setLogs((prev) => [...prev, `[INFO] ${data.message}`])
        } else if (data.type === 'platforms') {
          setLogs((prev) => [...prev, `[ATS] Scanning platforms: ${data.platforms.join(', ')}`])
        } else if (data.type === 'platform_result') {
          setPlatformStats((prev) => ({ ...prev, [data.platform]: data.count }))
          setLogs((prev) => [...prev, `[FETCH] ${data.platform.toUpperCase()}: ${data.count} listings`])
        } else if (data.type === 'summary') {
          setSummary({
            total: data.total_fetched,
            matched: data.after_filters,
            newCount: data.new_count,
          })
          setLogs((prev) => [
            ...prev,
            `[SUMMARY] ${data.total_fetched} total fetched | ${data.after_filters} matched preferences | ${data.new_count} new`,
          ])
        } else if (data.type === 'complete') {
          setLogs((prev) => [...prev, `[SUCCESS] ${data.message}`])
          setIsScanning(false)
          setIsCompleted(true)
          es.close()
          onScanFinished()
        } else if (data.type === 'error') {
          setLogs((prev) => [...prev, `[ERROR] ${data.message}`])
          setIsScanning(false)
          es.close()
        }
      } catch (e) {
        setLogs((prev) => [...prev, event.data])
      }
    }

    es.onerror = (err) => {
      console.error('SSE Error:', err)
      setLogs((prev) => [...prev, '[CONNECTION] Stream ended or connection closed.'])
      setIsScanning(false)
      es.close()
    }
  }

  const handleClose = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }
    setIsScanning(false)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white w-full max-w-3xl rounded-2xl overflow-hidden shadow-2xl border border-slate-200 flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-white">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-[#edf3f8] text-[#0a66c2]">
              <Terminal className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-base">Autonomous ATS Job Scanner</h3>
              <p className="text-xs text-slate-500">
                Scraping Lever, Greenhouse, Ashby, Workable, SmartRecruiters & direct career boards
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="text-slate-400 hover:text-slate-700 p-1.5 rounded-full hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Platform Stat Badges */}
        {Object.keys(platformStats).length > 0 && (
          <div className="px-6 py-3 bg-[#f8fafc] border-b border-slate-200 flex flex-wrap gap-2">
            {Object.entries(platformStats).map(([plat, count]) => (
              <div
                key={plat}
                className="px-3 py-1 rounded-full bg-white border border-slate-200 text-xs flex items-center gap-1.5 shadow-2xs"
              >
                <span className="capitalize text-slate-600 font-medium">{plat}:</span>
                <span className="text-[#0a66c2] font-bold">{count}</span>
              </div>
            ))}
          </div>
        )}

        {/* Summary Card */}
        {summary && (
          <div className="px-6 py-2.5 bg-[#edf3f8] border-b border-[#d0e2f5] flex items-center justify-between text-xs">
            <div className="text-slate-700 font-medium">
              Total fetched: <span className="text-slate-900 font-bold">{summary.total?.toLocaleString()}</span>
            </div>
            <div className="text-[#057642] font-bold">
              Matched: <span>{summary.matched?.toLocaleString()}</span>
            </div>
            <div className="text-[#0a66c2] font-bold">
              New listings: <span>{summary.newCount}</span>
            </div>
          </div>
        )}

        {/* Live Terminal Output Window */}
        <div className="p-4 sm:p-5 flex-1 overflow-hidden bg-slate-50 flex flex-col">
          <div className="flex-1 p-4 overflow-y-auto bg-[#181d23] rounded-xl border border-slate-800 font-mono text-xs text-slate-300 space-y-1.5 min-h-[260px] select-text shadow-inner">
            {logs.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 py-12">
                <Terminal className="w-8 h-8 mb-2 opacity-40 text-slate-400" />
                <p>Click "Start ATS Scan" to trigger the multi-ATS crawler.</p>
              </div>
            ) : (
              logs.map((log, idx) => {
                const isError = log.includes('[ERROR]') || log.includes('failed')
                const isSuccess = log.includes('[SUCCESS]') || log.includes('finished')
                const isInfo = log.includes('[FETCH]') || log.includes('[SUMMARY]')
                return (
                  <div
                    key={idx}
                    className={`leading-relaxed ${
                      isError
                        ? 'text-rose-400 font-semibold'
                        : isSuccess
                        ? 'text-emerald-400 font-semibold'
                        : isInfo
                        ? 'text-sky-300'
                        : 'text-slate-300'
                    }`}
                  >
                    {log}
                  </div>
                )
              })
            )}
            <div ref={logsEndRef} />
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-slate-200 bg-white flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            {isScanning ? (
              <span className="flex items-center gap-2 text-[#0a66c2] font-medium">
                <Loader2 className="w-4 h-4 animate-spin" />
                Scanning active boards...
              </span>
            ) : isCompleted ? (
              <span className="flex items-center gap-1.5 text-[#057642] font-bold">
                <CheckCircle2 className="w-4 h-4" />
                Scan complete! Jobs ranked and ready.
              </span>
            ) : (
              <span>Ready to scan ATS job boards</span>
            )}
          </div>

          <div className="flex items-center gap-2.5">
            {!isScanning && (
              <button
                onClick={startScan}
                className="px-5 py-2 rounded-full bg-[#0a66c2] hover:bg-[#004182] text-white text-xs font-bold flex items-center gap-2 shadow-xs transition-all cursor-pointer"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>{logs.length > 0 ? 'Restart Scan' : 'Start ATS Scan'}</span>
              </button>
            )}
            <button
              onClick={handleClose}
              className="px-4 py-2 rounded-full border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-semibold transition-all cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
