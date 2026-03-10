'use client'

import { useSystemStats } from '@/hooks/useSystemStats'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { formatBytes, formatDate } from '@/lib/utils'

export function SystemOverview() {
  const { stats, loading, error } = useSystemStats()

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[...Array(4)].map((_, i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <div className="h-4 bg-gray-200 rounded animate-pulse" />
            </CardHeader>
            <CardContent>
              <div className="h-8 bg-gray-200 rounded animate-pulse" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center text-red-500">
            <p>Error loading system stats: {error}</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!stats) return null

  const uptimeDays = Math.floor(stats.uptime / 86400)
  const uptimeHours = Math.floor((stats.uptime % 86400) / 3600)
  const uptimeMinutes = Math.floor((stats.uptime % 3600) / 60)

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            CPU Usage
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.cpu.usage.toFixed(1)}%</div>
          <p className="text-xs text-muted-foreground">
            {stats.cpu.cores} cores • Load: {stats.cpu.loadAverage[0].toFixed(2)}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Memory Usage
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {((stats.memory.used / stats.memory.total) * 100).toFixed(1)}%
          </div>
          <p className="text-xs text-muted-foreground">
            {formatBytes(stats.memory.used)} / {formatBytes(stats.memory.total)}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Disk Usage
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.disk.usage.toFixed(1)}%</div>
          <p className="text-xs text-muted-foreground">
            {formatBytes(stats.disk.used)} / {formatBytes(stats.disk.total)}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Uptime
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {uptimeDays}d {uptimeHours}h {uptimeMinutes}m
          </div>
          <p className="text-xs text-muted-foreground">
            Last updated: {formatDate(new Date())}
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
