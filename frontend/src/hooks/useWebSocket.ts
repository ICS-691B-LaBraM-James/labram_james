import { useCallback, useRef } from 'react'
import type { EEGFindings } from '../types'

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000/ws/stream'

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

      ws.onopen = () => {
        ws.send(
          JSON.stringify({
            message,
            patient_metadata: metadata,
            has_eeg: file !== null,
          }),
        )

        if (file) {
          file.arrayBuffer().then((buf) => ws.send(buf))
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
              onComplete()
              ws.close()
              break
            case 'error':
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

      ws.onclose = () => {
        wsRef.current = null
      }
    },
    [onToken, onStep, onFindings, onReport, onComplete, onError],
  )

  return { sendMessage }
}
