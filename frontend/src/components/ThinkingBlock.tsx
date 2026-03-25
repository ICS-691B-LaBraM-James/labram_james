import { useState, useEffect } from 'react'
import type { PipelineStep } from '../types'

interface Props {
  steps: PipelineStep[]
}

function StepIcon({ status }: { status: PipelineStep['status'] }) {
  if (status === 'completed') {
    return (
      <svg className="h-4 w-4 text-emerald-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
      </svg>
    )
  }
  if (status === 'in_progress') {
    return (
      <div className="h-4 w-4 shrink-0 flex items-center justify-center">
        <div className="h-3 w-3 rounded-full border-2 border-emerald-400 border-t-transparent animate-spin" />
      </div>
    )
  }
  return <div className="h-4 w-4 shrink-0 flex items-center justify-center"><div className="h-1.5 w-1.5 rounded-full bg-white/20" /></div>
}

function ThinkingBlock({ steps }: Props) {
  const allDone = steps.length > 0 && steps.every((s) => s.status === 'completed')
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    if (allDone) {
      const t = setTimeout(() => setCollapsed(true), 800)
      return () => clearTimeout(t)
    }
  }, [allDone])

  const activeStep = steps.find((s) => s.status === 'in_progress')
  const headerText = allDone
    ? `Analyzed EEG (${steps.length} steps)`
    : activeStep
      ? activeStep.label + '...'
      : 'Processing...'

  return (
    <div className="mb-3">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-2 text-xs text-white/50 hover:text-white/70 transition-colors group"
      >
        <svg
          className={`h-3 w-3 transition-transform ${collapsed ? '' : 'rotate-90'}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
        </svg>
        {!allDone && (
          <div className="h-3 w-3 rounded-full border-[1.5px] border-emerald-400 border-t-transparent animate-spin" />
        )}
        {allDone && (
          <svg className="h-3 w-3 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        )}
        <span>{headerText}</span>
      </button>

      {!collapsed && (
        <div className="mt-2 ml-1 pl-3 border-l-2 border-white/10 space-y-2">
          {steps.map((s) => (
            <div key={s.step} className="flex items-center gap-2.5">
              <StepIcon status={s.status} />
              <span className={`text-xs ${s.status === 'completed' ? 'text-white/50' : s.status === 'in_progress' ? 'text-white/80' : 'text-white/30'}`}>
                {s.label}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ThinkingBlock
