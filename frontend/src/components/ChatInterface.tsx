import { useState, useRef, useEffect, useCallback } from 'react'
import type { MessageAttachments } from '../types'
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

const INITIAL_METADATA = {
  age: '',
  sex: '', 
  mmse: '',
  medications: '',
  symptoms: '',
  recordingState: 'eyes_closed',
  history: {
    memoryLoss: false,
    executiveDysfunction: false,
    behavioralChanges: false,
    languageDifficulty: false,
    familyHistory: false,
    hypertension: false
  }
}

interface Props {
  eegFile: File | null
  onFileSelect: (file: File | null) => void
}

function ChatInterface({ eegFile, onFileSelect }: Props) {
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showMetadataForm, setShowMetadataForm] = useState(true)
  
  const [metadata, setMetadata] = useState(() => {
    const saved = localStorage.getItem('eeg_metadata')
    return saved ? JSON.parse(saved) : INITIAL_METADATA
  })

  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const {
    messages, addMessage, appendToLastMessage, updateLastMessageStep,
    setLastMessageFindings, setLastMessageReport, clearMessages,
  } = useChat()

  const { sendMessage } = useWebSocket({
    onToken: (t) => appendToLastMessage(t),
    onStep: (s, st) => updateLastMessageStep(s, st as any),
    onFindings: (f) => setLastMessageFindings(f),
    onReport: (r) => setLastMessageReport(r),
    onComplete: () => setIsLoading(false),
    onError: (e) => { appendToLastMessage(`\n\nError: ${e}`); setIsLoading(false); },
  })

  useEffect(() => {
    localStorage.setItem('eeg_metadata', JSON.stringify(metadata))
  }, [metadata])

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


  const handlePromptClick = (prompt: string) => {
    setInput(prompt)
    setTimeout(() => {
      textareaRef.current?.focus()
      autoResize()
    }, 0)
  }

  const handleSend = () => {
    const text = input.trim()
    if ((!text && !eegFile) || isLoading) return

    const query = text || 'Analyze clinical EEG signal';

    const presentIndications = Object.entries(metadata.history)
      .filter(([, present]) => present)
      .map(([key]) => key.replace(/([A-Z])/g, ' $1').toLowerCase().trim())
      .join(', ');

    const vitals: NonNullable<MessageAttachments['vitals']> = [];
    if (metadata.age?.trim()) vitals.push({ label: 'Age', value: metadata.age.trim() });
    if (metadata.sex?.trim()) vitals.push({ label: 'Sex', value: metadata.sex.trim() });
    if (metadata.mmse?.trim()) vitals.push({ label: 'MMSE', value: metadata.mmse.trim() });

    const notes: NonNullable<MessageAttachments['notes']> = [];
    if (metadata.symptoms?.trim()) notes.push({ label: 'Symptoms', value: metadata.symptoms.trim() });
    if (metadata.medications?.trim()) notes.push({ label: 'Medications', value: metadata.medications.trim() });
    if (presentIndications) notes.push({ label: 'Indications', value: presentIndications });

    const attachments: MessageAttachments = {};
    if (eegFile) attachments.fileName = eegFile.name;
    if (vitals.length > 0) attachments.vitals = vitals;
    if (notes.length > 0) attachments.notes = notes;
    const hasAttachments =
      Boolean(attachments.fileName) ||
      (attachments.vitals?.length ?? 0) > 0 ||
      (attachments.notes?.length ?? 0) > 0;

    addMessage('user', query, hasAttachments ? attachments : undefined);
    addMessage('assistant', '');
    setInput('');
    setIsLoading(true);
    setShowMetadataForm(false);
    
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    
    const submissionMetadata = {
      age: metadata.age,
      sex: metadata.sex,
      mmse: metadata.mmse,
      medications: metadata.medications,
      symptoms: metadata.symptoms,
      recording_state: metadata.recordingState,
      history: JSON.stringify(metadata.history)
    }
    
    sendMessage(text, eegFile, submissionMetadata)
    if (eegFile) onFileSelect(null)
  }

  const handleNewChat = () => {
    clearMessages(); setMetadata(INITIAL_METADATA);
    localStorage.removeItem('eeg_metadata'); setShowMetadataForm(true);
  }

  const isEmpty = messages.length === 0

  return (
    <div className="flex flex-col h-screen bg-[#0f0f0f]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-2.5">
          <div className="h-7 w-7 rounded-lg bg-emerald-600 flex items-center justify-center text-white">
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47 2.47a2.25 2.25 0 01-1.591.659H9.061a2.25 2.25 0 01-1.591-.659L5 14.5m14 0V17a2 2 0 01-2 2H7a2 2 0 01-2-2v-2.5" />
            </svg>
          </div>
          <span className="text-sm font-medium text-white/90">EEG Interpreter</span>
        </div>
        {messages.length > 0 && (
          <button onClick={handleNewChat} className="text-xs text-white/40 hover:text-white/70 px-3 py-1.5 rounded-lg hover:bg-white/5 transition-colors">New chat</button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full px-4 -mt-12">
            <div className="h-12 w-12 rounded-2xl bg-emerald-600 flex items-center justify-center mb-5 shadow-lg shadow-emerald-900/20">
               <svg className="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47 2.47a2.25 2.25 0 01-1.591.659H9.061a2.25 2.25 0 01-1.591-.659L5 14.5m14 0V17a2 2 0 01-2 2H7a2 2 0 01-2-2v-2.5" />
              </svg>
            </div>
            <h1 className="text-2xl font-semibold text-white mb-2">EEG Interpreter</h1>
            <p className="text-sm text-white/40 mb-8 text-center max-w-md">Upload clinical data for neural pipeline synthesis.</p>
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
            {messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <div className="border-t border-white/10 bg-[#0f0f0f] pb-6">
        <div className="max-w-3xl mx-auto px-4">
          {showMetadataForm && (
            <div className="mb-4 mt-4 bg-white/5 border border-white/10 rounded-2xl p-4 space-y-4 animate-in fade-in slide-in-from-bottom-2">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <input type="number" placeholder="Age" className="bg-[#1a1a1a] border border-white/10 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-emerald-500/50" value={metadata.age} onChange={(e) => setMetadata({...metadata, age: e.target.value})} />
                <select className="bg-[#1a1a1a] border border-white/10 rounded-lg px-3 py-2 text-sm text-white outline-none" value={metadata.sex} onChange={(e) => setMetadata({...metadata, sex: e.target.value})}>
                  <option value="">Sex</option>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                </select>
                <input type="number" placeholder="MMSE" className="bg-[#1a1a1a] border border-white/10 rounded-lg px-3 py-2 text-sm text-white outline-none" value={metadata.mmse} onChange={(e) => setMetadata({...metadata, mmse: e.target.value})} />
                <select className="bg-[#1a1a1a] border border-white/10 rounded-lg px-3 py-2 text-sm text-white outline-none" value={metadata.recordingState} onChange={(e) => setMetadata({...metadata, recordingState: e.target.value})}>
                  <option value="eyes_closed">Eyes Closed</option>
                  <option value="eyes_open">Eyes Open</option>
                </select>
              </div>

              <input type="text" placeholder="Reported Symptoms..." className="w-full bg-[#1a1a1a] border border-white/10 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-emerald-500/50" value={metadata.symptoms} onChange={(e) => setMetadata({...metadata, symptoms: e.target.value})} />
              <input type="text" placeholder="Current Medications..." className="w-full bg-[#1a1a1a] border border-white/10 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-emerald-500/50" value={metadata.medications} onChange={(e) => setMetadata({...metadata, medications: e.target.value})} />

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-y-2 gap-x-4 pt-1">
                {Object.entries({ memoryLoss: 'Memory Loss', executiveDysfunction: 'Executive Dysfunction', behavioralChanges: 'Behavioral Changes', languageDifficulty: 'Language Difficulty', familyHistory: 'Family History', hypertension: 'Hypertension' }).map(([key, label]) => (
                  <label key={key} className="flex items-center gap-2 text-[11px] text-white/40 cursor-pointer hover:text-white/70">
                    <input type="checkbox" className="rounded border-white/10 bg-white/5 text-emerald-600 focus:ring-0" checked={metadata.history[key as keyof typeof metadata.history]} onChange={(e) => setMetadata({...metadata, history: {...metadata.history, [key]: e.target.checked}})} />
                    {label}
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* File Preview Badge */}
          {eegFile && (
            <div className="flex items-center gap-2 mb-2 px-1 animate-in fade-in slide-in-from-bottom-2">
              <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-3 py-1.5">
                <svg className="h-4 w-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 22.5 12 13.5H3.75z" />
                </svg>
                <div className="flex flex-col">
                  <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-tight leading-none mb-0.5">
                    File Upload
                  </span>
                  <span className="text-[11px] text-white/60 truncate max-w-[200px]">
                    {eegFile.name}
                  </span>
                </div>
                <button 
                  onClick={() => onFileSelect(null)}
                  className="ml-2 p-1 hover:bg-emerald-500/20 rounded-md transition-colors text-emerald-400/50 hover:text-emerald-400"
                >
                  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          )}

          <div className="flex items-end gap-2 bg-white/5 border border-white/10 rounded-2xl px-3 py-2 focus-within:border-white/20 transition-all">
            <button 
              onClick={() => fileInputRef.current?.click()} 
              className={`p-1.5 transition-all rounded-lg hover:bg-white/5 ${
                eegFile 
                  ? 'text-emerald-400 bg-emerald-400/10 shadow-[0_0_10px_rgba(52,211,153,0.2)]' 
                  : 'text-white/30'
              }`}
            >
               <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" />
              </svg>
            </button>
            <input ref={fileInputRef} type="file" accept={ACCEPTED_EXTENSIONS.join(',')} onChange={(e) => onFileSelect(e.target.files?.[0] || null)} className="hidden" />
            <textarea ref={textareaRef} value={input} onChange={(e) => { setInput(e.target.value); autoResize(); }} onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()} disabled={isLoading} placeholder="Message EEG Interpreter..." rows={1} className="flex-1 bg-transparent text-sm text-white outline-none resize-none py-1.5 max-h-[200px]" />
            <button onClick={() => handleSend()} disabled={isLoading || (!input.trim() && !eegFile)} className="p-1.5 rounded-lg bg-white text-black disabled:opacity-20 transition-opacity">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
              </svg>
            </button>
          </div>
          <p className="text-[10px] text-white/20 text-center mt-2">AI-assisted clinical reporting. Requires professional review.</p>
        </div>
      </div>
    </div>
  )
}

export default ChatInterface
