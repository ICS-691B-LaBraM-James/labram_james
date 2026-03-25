import type { Message } from '../types'
import ThinkingBlock from './ThinkingBlock'
import FindingsCard from './FindingsCard'
import ReportCard from './ReportCard'

interface Props {
  message: Message
}

function MessageBubble({ message }: Props) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
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
          <p className="text-sm text-white/85 whitespace-pre-line leading-relaxed">{message.content}</p>
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
