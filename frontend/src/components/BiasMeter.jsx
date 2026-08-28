import React, { useEffect, useState, useRef } from 'react'
import { ShieldCheck, Activity, ChevronDown, ChevronUp } from 'lucide-react'

// Floating live bias-score indicator. Uses a shared window event 'gradeops:grade-tick'
// so any page can push a new grading tick that nudges the meter.
export default function BiasMeter() {
  const [score, setScore] = useState(0.024)
  const [history, setHistory] = useState(() => Array.from({ length: 24 }, () => 0.02 + Math.random() * 0.02))
  const [open, setOpen] = useState(true)
  const [pulse, setPulse] = useState(false)
  const timer = useRef(null)

  // ambient drift so the meter feels alive even without events
  useEffect(() => {
    timer.current = setInterval(() => {
      setScore((s) => {
        const drift = (Math.random() - 0.5) * 0.006
        const next = Math.max(0.005, Math.min(0.12, s + drift))
        setHistory((h) => [...h.slice(-23), next])
        return next
      })
    }, 1400)
    return () => clearInterval(timer.current)
  }, [])

  // external tick events (from grading batches or new uploads)
  useEffect(() => {
    const handler = (e) => {
      const delta = (e && e.detail && e.detail.delta) || (Math.random() - 0.4) * 0.02
      setScore((s) => {
        const next = Math.max(0.005, Math.min(0.15, s + delta))
        setHistory((h) => [...h.slice(-23), next])
        return next
      })
      setPulse(true)
      setTimeout(() => setPulse(false), 600)
    }
    window.addEventListener('gradeops:grade-tick', handler)
    return () => window.removeEventListener('gradeops:grade-tick', handler)
  }, [])

  const status = score < 0.03 ? 'excellent' : score < 0.06 ? 'nominal' : score < 0.09 ? 'watch' : 'alert'
  const statusColor = {
    excellent: '#22c55e',
    nominal: '#f59e0b',
    watch: '#f97316',
    alert: '#ef4444',
  }[status]

  // sparkline
  const w = 168, h = 40
  const min = Math.min(...history), max = Math.max(...history)
  const range = Math.max(0.005, max - min)
  const points = history.map((v, i) => {
    const x = (i / (history.length - 1)) * w
    const y = h - ((v - min) / range) * (h - 6) - 3
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')

  // radial gauge
  const pct = Math.min(1, score / 0.15)
  const R = 26, C = 2 * Math.PI * R
  const dash = C * pct

  return (
    <div className="fixed z-50 bottom-6 right-6 select-none">
      <div className={`relative rounded-2xl border border-gray-200 bg-white/90 backdrop-blur-xl shadow-lg transition-all ${pulse ? 'ring-1 ring-[#6b52c6]' : ''}`}>
        {/* Header */}
        <button
          onClick={() => setOpen((o) => !o)}
          className="w-full flex items-center gap-2 px-3 py-2 border-b border-gray-100"
        >
          <span className="w-2 h-2 rounded-full" style={{ background: statusColor, boxShadow: `0 0 8px ${statusColor}` }} />
          <ShieldCheck className="w-3.5 h-3.5 text-[#6b52c6]" />
          <span className="text-[11px] uppercase tracking-[0.2em] text-gray-500">Bias meter</span>
          <span className="ml-auto text-[10px] uppercase tracking-widest font-medium" style={{ color: statusColor }}>{status}</span>
          {open ? <ChevronDown className="w-3.5 h-3.5 text-gray-400" /> : <ChevronUp className="w-3.5 h-3.5 text-gray-400" />}
        </button>

        {open && (
          <div className="p-3 flex items-center gap-3">
            {/* Gauge */}
            <div className="relative w-[64px] h-[64px]">
              <svg width="64" height="64" viewBox="0 0 64 64">
                <circle cx="32" cy="32" r={R} stroke="#e5e7eb" strokeWidth="6" fill="none" />
                <circle
                  cx="32" cy="32" r={R}
                  stroke={statusColor}
                  strokeWidth="6"
                  fill="none"
                  strokeLinecap="round"
                  strokeDasharray={`${dash} ${C}`}
                  transform="rotate(-90 32 32)"
                  style={{ transition: 'stroke-dasharray .6s ease, stroke .3s ease' }}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <div className="font-display text-[15px] leading-none" style={{ color: statusColor }}>{score.toFixed(3)}</div>
                <div className="text-[9px] uppercase tracking-widest text-gray-400 mt-0.5">score</div>
              </div>
            </div>

            {/* Sparkline */}
            <div className="flex-1">
              <div className="flex items-center gap-1.5 mb-1">
                <Activity className="w-3 h-3 text-[#6b52c6]" />
                <span className="text-[10px] uppercase tracking-widest text-gray-500">Live · 24 papers</span>
              </div>
              <svg width={w} height={h} className="block">
                <defs>
                  <linearGradient id="sparkFill" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor={statusColor} stopOpacity="0.2" />
                    <stop offset="100%" stopColor={statusColor} stopOpacity="0" />
                  </linearGradient>
                </defs>
                <polyline points={`0,${h} ${points} ${w},${h}`} fill="url(#sparkFill)" stroke="none" />
                <polyline points={points} fill="none" stroke={statusColor} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <div className="flex items-center justify-between text-[10px] text-gray-400 mt-1">
                <span>Target &lt; 0.05</span>
                <span style={{ color: statusColor }}>{status === 'excellent' ? 'well below' : status === 'nominal' ? 'on target' : 'monitor'}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// Helper to trigger a bias tick from any component
export const emitGradeTick = (delta) => {
  window.dispatchEvent(new CustomEvent('gradeops:grade-tick', { detail: { delta } }))
}
