import { useState } from 'react'

interface Props {
  report: string
}

function ReportCard({ report }: Props) {
  const [expanded, setExpanded] = useState(true)
  const [copied, setCopied] = useState(false)

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation()
    await navigator.clipboard.writeText(report)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="mt-3 border border-white/10 rounded-xl overflow-hidden bg-white/[0.02]">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <svg className="h-4 w-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
          <span className="text-xs font-medium text-white/80">Clinical Report</span>
        </div>
        <div className="flex items-center gap-2">
          {expanded && (
            <button
              onClick={handleCopy}
              className="text-[10px] text-white/30 hover:text-white/60 transition-colors px-2 py-0.5 rounded hover:bg-white/5"
            >
              {copied ? 'Copied' : 'Copy'}
            </button>
          )}
          <svg
            className={`h-4 w-4 text-white/30 transition-transform ${expanded ? 'rotate-180' : ''}`}
            fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 pt-1">
          <pre className="text-xs text-white/60 whitespace-pre-wrap font-mono leading-relaxed">
            {report}
          </pre>
        </div>
      )}
    </div>
  )
}

export default ReportCard
