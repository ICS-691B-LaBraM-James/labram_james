import { useState } from 'react'
import type { EEGFindings } from '../types'

interface Props {
  findings: EEGFindings
}

function bandBadge(level: string) {
  const color =
    level === 'elevated'
      ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
      : level === 'reduced'
        ? 'bg-red-500/20 text-red-300 border-red-500/30'
        : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${color}`}>
      {level}
    </span>
  )
}

function FindingsCard({ findings }: Props) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div className="mt-3 border border-white/10 rounded-xl overflow-hidden bg-white/[0.02]">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <svg className="h-4 w-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5" />
          </svg>
          <span className="text-xs font-medium text-white/80">EEG Findings</span>
        </div>
        <svg
          className={`h-4 w-4 text-white/30 transition-transform ${expanded ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {expanded && (
        <div className="px-4 pb-4 pt-1 space-y-3 text-xs">
          <div className="grid grid-cols-2 gap-x-6 gap-y-2">
            <div>
              <span className="text-white/40">Cognitive State</span>
              <p className="text-white/80 mt-0.5">{findings.cognitive_state}</p>
            </div>
            <div>
              <span className="text-white/40">Emotional State</span>
              <p className="text-white/80 mt-0.5">{findings.emotional_state}</p>
            </div>
            <div>
              <span className="text-white/40">Dominant Shift</span>
              <p className="text-white/80 mt-0.5">{findings.dominant_frequency_shift}</p>
            </div>
            <div>
              <span className="text-white/40">Seizure Risk</span>
              <p className="text-white/80 mt-0.5">{findings.seizure_risk}</p>
            </div>
          </div>

          <div>
            <span className="text-white/40">Band Power</span>
            <div className="flex flex-wrap gap-1.5 mt-1.5">
              {Object.entries(findings.band_power).map(([band, level]) => (
                <div key={band} className="flex items-center gap-1.5 bg-white/5 rounded-lg px-2.5 py-1">
                  <span className="text-white/50 capitalize">{band}</span>
                  {bandBadge(level)}
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-white/40">AD Risk Score</span>
              <span className="text-white/60">{(findings.ad_risk_score * 100).toFixed(0)}%</span>
            </div>
            <div className="w-full bg-white/10 rounded-full h-1.5">
              <div
                className="bg-amber-500 h-1.5 rounded-full transition-all"
                style={{ width: `${findings.ad_risk_score * 100}%` }}
              />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-white/40">Confidence</span>
            <span className="text-white/60">{(findings.confidence * 100).toFixed(0)}%</span>
          </div>

          {findings.notable_patterns.length > 0 && (
            <div>
              <span className="text-white/40">Notable Patterns</span>
              <ul className="mt-1 space-y-0.5">
                {findings.notable_patterns.map((p, i) => (
                  <li key={i} className="text-white/60 flex items-start gap-1.5">
                    <span className="text-white/20 mt-0.5">•</span>
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default FindingsCard
