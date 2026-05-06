export interface PipelineStep {
  step: string
  label: string
  status: 'pending' | 'in_progress' | 'completed'
}

export interface MessageAttachments {
  fileName?: string
  vitals?: Array<{ label: string; value: string }>
  notes?: Array<{ label: string; value: string }>
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  steps?: PipelineStep[]
  findings?: EEGFindings | null
  report?: string | null
  attachments?: MessageAttachments
}

export interface BandPower {
  delta: number
  theta: number
  alpha: number
  beta: number
  gamma: number
}

export interface EEGFindings {
  cognitive_state: string
  emotional_state: string
  dominant_frequency_shift: string
  band_power: BandPower
  ad_risk_score: number
  seizure_risk: string
  confidence: number
  notable_patterns: string[]
}

export interface ChatResponse {
  response: string
  findings?: EEGFindings | null
  report?: string | null
}
