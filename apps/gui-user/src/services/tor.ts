import { SocksProxyAgent } from 'socks-proxy-agent'

export class TorClient {
  private agent: SocksProxyAgent

  constructor() {
    const torSocksPort = process.env.TOR_SOCKS_PORT || '9050'
    this.agent = new SocksProxyAgent(`socks5://127.0.0.1:${torSocksPort}`)
  }

  async makeRequest(url: string, options: RequestInit = {}): Promise<Response> {
    // Ensure URL is .onion
    if (!url.includes('.onion')) {
      throw new Error('Only .onion URLs allowed in Tor environment')
    }
    
    return fetch(url, {
      ...options,
      agent: this.agent as any
    })
  }

  async healthCheck(): Promise<boolean> {
    try {
      // Test Tor connectivity by making a request through the proxy
      const response = await this.makeRequest('http://check.torproject.org/api/ip')
      return response.ok
    } catch (error) {
      console.error('Tor health check failed:', error)
      return false
    }
  }

  async getTorStatus(): Promise<{ connected: boolean; ip?: string; country?: string }> {
    try {
      const response = await this.makeRequest('http://check.torproject.org/api/ip')
      if (response.ok) {
        const data = await response.json()
        return {
          connected: true,
          ip: data.IP,
          country: data.Country
        }
      }
      return { connected: false }
    } catch (error) {
      console.error('Failed to get Tor status:', error)
      return { connected: false }
    }
  }
}
