import type { Message } from '../types'
import ThinkingBlock from './ThinkingBlock'
import FindingsCard from './FindingsCard'
import ReportCard from './ReportCard'
import MarkdownContent from './MarkdownContent'

interface Props {
  message: Message
}

function MessageBubble({ message }: Props) {
  if (message.role === 'user') {
    const a = message.attachments
    const hasFile = Boolean(a?.fileName)
    const hasVitals = Boolean(a?.vitals && a.vitals.length > 0)
    const hasNotes = Boolean(a?.notes && a.notes.length > 0)
    const hasAttachments = hasFile || hasVitals || hasNotes

    return (
      <div className="flex flex-col items-end gap-2">
        {hasAttachments && (
          <div className="max-w-[75%] w-fit min-w-[260px] bg-white/[0.04] border border-white/10 rounded-2xl overflow-hidden divide-y divide-white/10">
            {hasFile && (
              <div className="flex items-center gap-2 px-3.5 py-2.5">
                <svg
                  className="h-3.5 w-3.5 text-emerald-400 shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                  />
                </svg>
                <span className="text-xs text-white/80 truncate">{a!.fileName}</span>
              </div>
            )}
            {hasVitals && (
              <div className="flex flex-wrap gap-x-4 gap-y-1 px-3.5 py-2.5">
                {a!.vitals!.map((f) => (
                  <div key={f.label} className="text-xs">
                    <span className="text-white/40">{f.label} </span>
                    <span className="text-white/85">{f.value}</span>
                  </div>
                ))}
              </div>
            )}
            {hasNotes &&
              a!.notes!.map((f) => (
                <div key={f.label} className="px-3.5 py-2 space-y-0.5">
                  <div className="text-[10px] uppercase tracking-wide text-white/40">
                    {f.label}
                  </div>
                  <div className="text-xs text-white/85 whitespace-pre-line break-words">
                    {f.value}
                  </div>
                </div>
              ))}
          </div>
        )}
        <div className="max-w-[75%] bg-white/10 rounded-2xl rounded-br-md px-4 py-2.5">
          <p className="text-sm text-white whitespace-pre-line">{message.content}</p>
        </div>
      </div>
    )
  }

  const hasSteps = message.steps && message.steps.length > 0
  const hasContent = message.content.trim().length > 0

  return (
    <div className="flex gap-3">
      <div className="shrink-0 mt-0.5">
        <div className="h-7 w-7 rounded-full bg-emerald-600 flex items-center justify-center">
          <svg className="h-3.5 w-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47 2.47a2.25 2.25 0 01-1.591.659H9.061a2.25 2.25 0 01-1.591-.659L5 14.5m14 0V17a2 2 0 01-2 2H7a2 2 0 01-2-2v-2.5" />
          </svg>
        </div>
      </div>
      <div className="flex-1 min-w-0">
        {hasSteps && <ThinkingBlock steps={message.steps!} />}
        {hasContent && (
          <MarkdownContent className="text-white/85">{message.content}</MarkdownContent>
        )}
        {!hasContent && !hasSteps && (
          <div className="flex items-center gap-1.5 h-5">
            <div className="h-1.5 w-1.5 rounded-full bg-white/30 animate-pulse" />
            <div className="h-1.5 w-1.5 rounded-full bg-white/30 animate-pulse [animation-delay:150ms]" />
            <div className="h-1.5 w-1.5 rounded-full bg-white/30 animate-pulse [animation-delay:300ms]" />
          </div>
        )}
        {message.findings && <FindingsCard findings={message.findings} />}
        {message.report && <ReportCard report={message.report} />}
      </div>
    </div>
  )
}

export default MessageBubble
