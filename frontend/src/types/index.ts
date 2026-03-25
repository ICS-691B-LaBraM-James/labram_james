export interface PipelineStep {
  step: string
  label: string
  status: 'pending' | 'in_progress' | 'completed'
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  steps?: PipelineStep[]
  findings?: EEGFindings | null
  report?: string | null
}

export interface BandPower {
  delta: string
  theta: string
  alpha: string
  beta: string
  gamma: string
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
