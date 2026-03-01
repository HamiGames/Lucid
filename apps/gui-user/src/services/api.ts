import { TorClient } from './tor'

const API_BASE_URL = process.env.API_BASE_URL || 'https://sessions-gateway.onion'
const torClient = new TorClient()

class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public statusText: string
  ) {
    super(message)
    this.name = 'APIError'
  }
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}/api${endpoint}`
  
  try {
    const response = await torClient.makeRequest(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })

    if (!response.ok) {
      throw new APIError(
        `API request failed: ${response.statusText}`,
        response.status,
        response.statusText
      )
    }

    return await response.json()
  } catch (error) {
    if (error instanceof APIError) {
      throw error
    }
    throw new APIError(
      `Network error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      0,
      'Network Error'
    )
  }
}

export const SessionAPI = {
  async getSessions() {
    return apiRequest<Session[]>('/sessions')
  },

  async getSession(id: string) {
    return apiRequest<Session>(`/sessions/${id}`)
  },

  async connect(sessionId: string) {
    return apiRequest(`/sessions/${sessionId}/connect`, {
      method: 'POST',
    })
  },

  async disconnect(sessionId: string) {
    return apiRequest(`/sessions/${sessionId}/disconnect`, {
      method: 'POST',
    })
  },

  async reconnect(sessionId: string) {
    return apiRequest(`/sessions/${sessionId}/reconnect`, {
      method: 'POST',
    })
  },

  async createSession(sessionData: CreateSessionData) {
    return apiRequest<Session>('/sessions', {
      method: 'POST',
      body: JSON.stringify(sessionData),
    })
  },

  async deleteSession(sessionId: string) {
    return apiRequest(`/sessions/${sessionId}`, {
      method: 'DELETE',
    })
  },
}

export const PolicyAPI = {
  async getPolicy() {
    return apiRequest<Policy>('/policy')
  },

  async updatePolicy(policy: Policy) {
    return apiRequest('/policy', {
      method: 'PUT',
      body: JSON.stringify(policy),
    })
  },
}

export const ProofsAPI = {
  async getProofs() {
    return apiRequest<Proof[]>('/proofs')
  },

  async getProof(id: string) {
    return apiRequest<Proof>(`/proofs/${id}`)
  },

  async exportProof(id: string, format: 'json' | 'pdf' = 'json') {
    return apiRequest<Blob>(`/proofs/${id}/export?format=${format}`)
  },
}

export const AuthAPI = {
  async login(email: string, password: string) {
    return apiRequest<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  },

  async logout() {
    return apiRequest('/auth/logout', {
      method: 'POST',
    })
  },

  async refreshToken() {
    return apiRequest<AuthResponse>('/auth/refresh', {
      method: 'POST',
    })
  },

  async sendMagicLink(email: string) {
    return apiRequest('/auth/magic-link', {
      method: 'POST',
      body: JSON.stringify({ email }),
    })
  },

  async verifyMagicLink(token: string) {
    return apiRequest<AuthResponse>('/auth/verify-magic-link', {
      method: 'POST',
      body: JSON.stringify({ token }),
    })
  },

  async setupTOTP() {
    return apiRequest<TOTPSetup>('/auth/totp/setup', {
      method: 'POST',
    })
  },

  async verifyTOTP(code: string) {
    return apiRequest<AuthResponse>('/auth/totp/verify', {
      method: 'POST',
      body: JSON.stringify({ code }),
    })
  },
}

// Types
export interface Session {
  id: string
  name: string
  status: 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'failed'
  host: string
  port: number
  createdAt: string
  lastConnected?: string
}

export interface CreateSessionData {
  name: string
  host: string
  port: number
  username?: string
}

export interface Policy {
  mouseEnabled: boolean
  keyboardEnabled: boolean
  clipboardEnabled: boolean
  fileTransferEnabled: boolean
  deviceRedirectEnabled: boolean
  audioEnabled: boolean
  videoEnabled: boolean
  privacyShieldEnabled: boolean
  maxBitrate: number
  compressionLevel: number
  encryptionLevel: 'none' | 'basic' | 'standard' | 'high'
  sessionTimeout: number
}

export interface Proof {
  id: string
  sessionId: string
  timestamp: string
  type: 'connection' | 'activity' | 'disconnection'
  data: Record<string, any>
  hash: string
}

export interface AuthResponse {
  token: string
  refreshToken: string
  user: User
  expiresIn: number
}

export interface User {
  id: string
  email: string
  name?: string
  totpEnabled: boolean
}

export interface TOTPSetup {
  secret: string
  qrCode: string
}
