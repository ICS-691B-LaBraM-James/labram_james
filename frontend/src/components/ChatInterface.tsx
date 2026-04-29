import { useState, useRef, useEffect, useCallback } from 'react'
import type { EEGFindings } from '../types'
import { useChat } from '../hooks/useChat'
import { useWebSocket } from '../hooks/useWebSocket'
import MessageBubble from './MessageBubble'

const ACCEPTED_EXTENSIONS = ['.edf', '.fif', '.set', '.csv']

const SUGGESTED_PROMPTS = [
  'Analyze my EEG recording',
  'What patterns indicate seizure risk?',
  'Explain alpha wave suppression',
  'How is Alzheimer\'s detected in EEG?',
]

interface Props {
  eegFile: File | null
  onFileSelect: (file: File | null) => void
}

function ChatInterface({ eegFile, onFileSelect }: Props) {
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const {
    messages,
    addMessage,
    appendToLastMessage,
    updateLastMessageStep,
    setLastMessageFindings,
    setLastMessageReport,
    clearMessages,
  } = useChat()

  const { sendMessage } = useWebSocket({
    onToken: (token) => appendToLastMessage(token),
    onStep: (step, status) => updateLastMessageStep(step, status as 'pending' | 'in_progress' | 'completed'),
    onFindings: (findings: EEGFindings) => setLastMessageFindings(findings),
    onReport: (report: string) => setLastMessageReport(report),
    onComplete: () => setIsLoading(false),
    onError: (error) => {
      appendToLastMessage(`\n\nError: ${error}`)
      setIsLoading(false)
    },
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const autoResize = useCallback(() => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 200) + 'px'
    }
  }, [])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || isLoading) return

    addMessage('user', text)
    addMessage('assistant', '')
    setInput('')
    setIsLoading(true)
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
    const file = eegFile
    await sendMessage(text, file)
    onFileSelect(null)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handlePromptClick = (prompt: string) => {
    setInput(prompt)
    textareaRef.current?.focus()
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null
    onFileSelect(file)
    if (e.target) e.target.value = ''
  }

  const isEmpty = messages.length === 0

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-2.5">
          <div className="h-7 w-7 rounded-lg bg-emerald-600 flex items-center justify-center">
            <svg className="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47 2.47a2.25 2.25 0 01-1.591.659H9.061a2.25 2.25 0 01-1.591-.659L5 14.5m14 0V17a2 2 0 01-2 2H7a2 2 0 01-2-2v-2.5" />
            </svg>
          </div>
          <span className="text-sm font-medium text-white/90">EEG Interpreter</span>
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearMessages}
            className="text-xs text-white/40 hover:text-white/70 transition-colors px-3 py-1.5 rounded-lg hover:bg-white/5"
          >
            New chat
          </button>
        )}
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full px-4 -mt-12">
            <div className="h-12 w-12 rounded-2xl bg-emerald-600 flex items-center justify-center mb-5">
              <svg className="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47 2.47a2.25 2.25 0 01-1.591.659H9.061a2.25 2.25 0 01-1.591-.659L5 14.5m14 0V17a2 2 0 01-2 2H7a2 2 0 01-2-2v-2.5" />
              </svg>
            </div>
            <h1 className="text-2xl font-semibold text-white mb-2">EEG Interpreter</h1>
            <p className="text-sm text-white/40 mb-8 text-center max-w-md">
              Upload an EEG file and ask questions, or explore neurology topics.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-lg">
              {SUGGESTED_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => handlePromptClick(prompt)}
                  className="text-left text-sm text-white/60 hover:text-white/90 border border-white/10 hover:border-white/20 rounded-xl px-4 py-3 transition-colors hover:bg-white/5"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="border-t border-white/10 bg-[#0f0f0f]">
        <div className="max-w-3xl mx-auto px-4 py-3">
          {eegFile && (
            <div className="flex items-center gap-2 mb-2 px-1">
              <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs">
                <svg className="h-3.5 w-3.5 text-emerald-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
                <span className="text-white/70 truncate max-w-[200px]">{eegFile.name}</span>
                <button
                  onClick={() => onFileSelect(null)}
                  className="text-white/30 hover:text-white/70 transition-colors ml-1"
                >
                  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          )}
          <div className="flex items-end gap-2 bg-white/5 border border-white/10 rounded-2xl px-3 py-2">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="shrink-0 p-1.5 text-white/30 hover:text-white/60 transition-colors rounded-lg hover:bg-white/5"
              title="Attach EEG file"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" />
              </svg>
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_EXTENSIONS.join(',')}
              onChange={handleFileChange}
              className="hidden"
            />
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => {
                setInput(e.target.value)
                autoResize()
              }}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              placeholder="Message EEG Interpreter..."
              rows={1}
              className="flex-1 bg-transparent text-sm text-white placeholder-white/30 resize-none focus:outline-none disabled:opacity-50 py-1.5 max-h-[200px]"
            />
            <button
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              className="shrink-0 p-1.5 rounded-lg bg-white text-black disabled:opacity-20 disabled:bg-white/50 transition-opacity"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
              </svg>
            </button>
          </div>
          <p className="text-[10px] text-white/20 text-center mt-2">
            AI-generated analysis requires clinical review. Not a diagnostic tool.
          </p>
        </div>
      </div>
    </div>
  )
}

export default ChatInterface
