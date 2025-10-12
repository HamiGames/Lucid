'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { 
  Monitor, 
  Shield, 
  Database, 
  Wallet, 
  Activity,
  Settings,
  Users,
  FileText
} from 'lucide-react'

interface SystemStatus {
  services: {
    name: string
    status: 'healthy' | 'degraded' | 'unhealthy'
    uptime: string
  }[]
  blockchain: {
    connected: boolean
    lastBlock: number
    syncStatus: string
  }
  tron: {
    connected: boolean
    network: 'mainnet' | 'shasta'
    balance: string
  }
  storage: {
    used: string
    available: string
    total: string
  }
}

export default function Dashboard() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSystemStatus()
    const interval = setInterval(fetchSystemStatus, 30000) // Update every 30s
    return () => clearInterval(interval)
  }, [])

  const fetchSystemStatus = async () => {
    try {
      const response = await fetch('/api/system/status')
      const data = await response.json()
      setSystemStatus(data)
    } catch (error) {
      console.error('Failed to fetch system status:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-500'
      case 'degraded': return 'bg-yellow-500'
      case 'unhealthy': return 'bg-red-500'
      default: return 'bg-gray-500'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Lucid RDP Admin Dashboard</h1>
          <p className="text-gray-600 mt-2">Raspberry Pi 5 - Tor-only Remote Desktop Platform</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">System Health</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {systemStatus?.services.filter(s => s.status === 'healthy').length || 0}
                <span className="text-sm text-muted-foreground">/{systemStatus?.services.length || 0}</span>
              </div>
              <p className="text-xs text-muted-foreground">
                Services running
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Blockchain</CardTitle>
              <Shield className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {systemStatus?.blockchain.connected ? 'Connected' : 'Disconnected'}
              </div>
              <p className="text-xs text-muted-foreground">
                Block #{systemStatus?.blockchain.lastBlock || 'N/A'}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">TRON Network</CardTitle>
              <Wallet className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {systemStatus?.tron.network || 'Unknown'}
              </div>
              <p className="text-xs text-muted-foreground">
                {systemStatus?.tron.balance || '0'} USDT
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Storage</CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {systemStatus?.storage.used || '0 GB'}
              </div>
              <p className="text-xs text-muted-foreground">
                of {systemStatus?.storage.total || '0 GB'} used
              </p>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Monitor className="h-5 w-5" />
                Service Status
              </CardTitle>
              <CardDescription>
                Current status of all system services
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {systemStatus?.services.map((service, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-2 h-2 rounded-full ${getStatusColor(service.status)}`} />
                      <span className="font-medium">{service.name}</span>
                    </div>
                    <div className="text-right">
                      <Badge variant={service.status === 'healthy' ? 'default' : 'destructive'}>
                        {service.status}
                      </Badge>
                      <p className="text-xs text-muted-foreground mt-1">
                        {service.uptime}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Quick Actions
              </CardTitle>
              <CardDescription>
                Common administrative tasks
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3">
                <Button variant="outline" className="h-auto p-4 flex flex-col items-center gap-2">
                  <Users className="h-6 w-6" />
                  <span className="text-sm">Manage Sessions</span>
                </Button>
                <Button variant="outline" className="h-auto p-4 flex flex-col items-center gap-2">
                  <FileText className="h-6 w-6" />
                  <span className="text-sm">View Logs</span>
                </Button>
                <Button variant="outline" className="h-auto p-4 flex flex-col items-center gap-2">
                  <Shield className="h-6 w-6" />
                  <span className="text-sm">Security</span>
                </Button>
                <Button variant="outline" className="h-auto p-4 flex flex-col items-center gap-2">
                  <Database className="h-6 w-6" />
                  <span className="text-sm">Backup</span>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
