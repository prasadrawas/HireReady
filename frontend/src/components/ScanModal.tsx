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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="glass-panel w-full max-w-3xl rounded-2xl overflow-hidden shadow-2xl border border-slate-700/60 flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <Terminal className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold text-white text-base">Autonomous ATS Job Scanner</h3>
              <p className="text-xs text-slate-400">Lever, Greenhouse, Ashby, Workable, SmartRecruiters & more</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800/80 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Platform Stat Badges */}
        {Object.keys(platformStats).length > 0 && (
          <div className="px-6 py-3 bg-slate-900/40 border-b border-slate-800/60 flex flex-wrap gap-2">
            {Object.entries(platformStats).map(([plat, count]) => (
              <div
                key={plat}
                className="px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700 text-xs flex items-center gap-1.5"
              >
                <span className="capitalize text-slate-300 font-medium">{plat}:</span>
                <span className="text-blue-400 font-semibold">{count}</span>
              </div>
            ))}
          </div>
        )}

        {/* Summary Card */}
        {summary && (
          <div className="px-6 py-3 bg-blue-950/20 border-b border-blue-900/40 flex items-center justify-between text-xs">
            <div className="text-slate-300">
              Total: <span className="text-white font-semibold">{summary.total?.toLocaleString()}</span> listings
            </div>
            <div className="text-emerald-400 font-medium">
              Matched Preferences: <span className="font-bold">{summary.matched?.toLocaleString()}</span>
            </div>
            <div className="text-indigo-400 font-medium">
              New: <span className="font-bold">{summary.newCount}</span>
            </div>
          </div>
        )}

        {/* Live Terminal Output */}
        <div className="flex-1 p-5 overflow-y-auto bg-slate-950/90 font-mono text-xs text-slate-300 space-y-1.5 min-h-[300px] select-text">
          {logs.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-500 py-12">
              <Terminal className="w-8 h-8 mb-2 opacity-50" />
              <p>Click "Start ATS Scan" to begin scanning configured company job boards.</p>
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
                      ? 'text-red-400 font-semibold'
                      : isSuccess
                      ? 'text-emerald-400 font-semibold'
                      : isInfo
                      ? 'text-blue-300'
                      : 'text-slate-400'
                  }`}
                >
                  {log}
                </div>
              )
            })
          )}
          <div ref={logsEndRef} />
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-900/80 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            {isScanning ? (
              <span className="flex items-center gap-2 text-blue-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                Scanning active boards...
              </span>
            ) : isCompleted ? (
              <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
                <CheckCircle2 className="w-4 h-4" />
                Scan complete! Jobs ranked and ready.
              </span>
            ) : (
              <span>Ready to scan ATS job boards</span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {!isScanning && (
              <button
                onClick={startScan}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-blue-600/30 transition-all"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>{logs.length > 0 ? 'Restart Scan' : 'Start ATS Scan'}</span>
              </button>
            )}
            <button
              onClick={handleClose}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-all"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
