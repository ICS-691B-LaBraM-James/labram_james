import { useState, useCallback } from 'react'
import type { Message, EEGFindings, PipelineStep } from '../types'

const STEP_LABELS: Record<string, string> = {
  eeg_cleaning: 'Cleaning EEG data',
  labram_encoding: 'Encoding with LaBraM',
  cognitive_classification: 'Classifying cognitive state',
  neurological_detection: 'Detecting neurological patterns',
  report_generation: 'Generating clinical report',
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])

  const addMessage = useCallback((role: 'user' | 'assistant', content: string) => {
    const msg: Message = {
      id: crypto.randomUUID(),
      role,
      content,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, msg])
  }, [])

  const appendToLastMessage = useCallback((text: string) => {
    setMessages((prev) => {
      const updated = [...prev]
      for (let i = updated.length - 1; i >= 0; i--) {
        if (updated[i].role === 'assistant') {
          updated[i] = { ...updated[i], content: updated[i].content + text }
          break
        }
      }
      return updated
    })
  }, [])

  const updateLastMessageStep = useCallback((step: string, status: PipelineStep['status']) => {
    setMessages((prev) => {
      const updated = [...prev]
      for (let i = updated.length - 1; i >= 0; i--) {
        if (updated[i].role === 'assistant') {
          const existing = updated[i].steps ?? []
          const idx = existing.findIndex((s) => s.step === step)
          const entry: PipelineStep = {
            step,
            label: STEP_LABELS[step] ?? step,
            status,
          }
          const newSteps = idx >= 0
            ? existing.map((s, j) => (j === idx ? entry : s))
            : [...existing, entry]
          updated[i] = { ...updated[i], steps: newSteps }
          break
        }
      }
      return updated
    })
  }, [])

  const setLastMessageFindings = useCallback((findings: EEGFindings) => {
    setMessages((prev) => {
      const updated = [...prev]
      for (let i = updated.length - 1; i >= 0; i--) {
        if (updated[i].role === 'assistant') {
          updated[i] = { ...updated[i], findings }
          break
        }
      }
      return updated
    })
  }, [])

  const setLastMessageReport = useCallback((report: string) => {
    setMessages((prev) => {
      const updated = [...prev]
      for (let i = updated.length - 1; i >= 0; i--) {
        if (updated[i].role === 'assistant') {
          updated[i] = { ...updated[i], report }
          break
        }
      }
      return updated
    })
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  return {
    messages,
    addMessage,
    appendToLastMessage,
    updateLastMessageStep,
    setLastMessageFindings,
    setLastMessageReport,
    clearMessages,
  }
}
