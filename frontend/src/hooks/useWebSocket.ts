import { useCallback, useRef } from 'react'
import type { EEGFindings } from '../types'

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://127.0.0.1:8000/ws/stream'

interface UseWebSocketOptions {
  onToken: (token: string) => void
  onStep: (step: string, status: string) => void
  onFindings: (findings: EEGFindings) => void
  onReport: (report: string) => void
  onComplete: () => void
  onError: (error: string) => void
}

export function useWebSocket({ onToken, onStep, onFindings, onReport, onComplete, onError }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null)

  const sendMessage = useCallback(
    (message: string, file: File | null, metadata: any) => {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws
      let finished = false

      ws.onopen = () => {
        ws.send(
          JSON.stringify({
            message,
            patient_metadata: metadata,
            has_eeg: file !== null,
          }),
        )
          if (file) {
            ws.send(file)
          }
      }

      ws.onmessage = (event) => {
        try {
          const frame = JSON.parse(event.data)
          switch (frame.type) {
            case 'token':
              onToken(frame.content)
              break
            case 'step':
              onStep(frame.step, frame.status)
              break
            case 'findings':
              onFindings(frame.data)
              break
            case 'report':
              onReport(frame.data)
              break
            case 'done':
              finished = true
              onComplete()
              ws.close()
              break
            case 'error':
              finished = true
              onError(frame.message)
              ws.close()
              break
          }
        } catch {
          onError('Failed to parse server message')
        }
      }

      ws.onerror = () => {
        onError('WebSocket connection error')
      }

      ws.onclose = (event) => {
        wsRef.current = null
        if (!finished) {
          const detail =
            event.code !== 1000 && event.code !== 1005
              ? ` (WebSocket ${event.code}${event.reason ? `: ${event.reason}` : ''})`
              : ''
          onError(`Connection closed before completion${detail}`)
        }
      }
    },
    [onToken, onStep, onFindings, onReport, onComplete, onError],
  )

  return { sendMessage }
}
