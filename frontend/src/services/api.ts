export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
export const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000/ws/stream'

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/health`)
    return res.ok
  } catch {
    return false
  }
}
