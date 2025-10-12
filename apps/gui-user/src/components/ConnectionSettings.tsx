'use client'

import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Save, Wifi, Shield, Globe, Settings } from 'lucide-react'
import { TorClient } from '@/services/tor'
import toast from 'react-hot-toast'

const settingsSchema = z.object({
  torSocksPort: z.number().min(1).max(65535),
  torControlPort: z.number().min(1).max(65535),
  apiBaseUrl: z.string().url(),
  connectionTimeout: z.number().min(1000).max(30000),
  retryAttempts: z.number().min(1).max(10),
  enableCompression: z.boolean(),
  enableEncryption: z.boolean(),
  logLevel: z.enum(['debug', 'info', 'warn', 'error']),
})

type SettingsFormData = z.infer<typeof settingsSchema>

export function ConnectionSettings() {
  const [torStatus, setTorStatus] = useState<{
    connected: boolean
    ip?: string
    country?: string
  }>({ connected: false })
  const [isLoadingTorStatus, setIsLoadingTorStatus] = useState(false)

  const { register, handleSubmit, watch, formState: { errors, isSubmitting } } = useForm<SettingsFormData>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      torSocksPort: 9050,
      torControlPort: 9051,
      apiBaseUrl: 'https://sessions-gateway.onion',
      connectionTimeout: 10000,
      retryAttempts: 3,
      enableCompression: true,
      enableEncryption: true,
      logLevel: 'info',
    }
  })

  const watchedValues = watch()

  useEffect(() => {
    checkTorStatus()
  }, [])

  const checkTorStatus = async () => {
    setIsLoadingTorStatus(true)
    try {
      const torClient = new TorClient()
      const status = await torClient.getTorStatus()
      setTorStatus(status)
    } catch (error) {
      console.error('Failed to check Tor status:', error)
      setTorStatus({ connected: false })
    } finally {
      setIsLoadingTorStatus(false)
    }
  }

  const onSubmit = async (data: SettingsFormData) => {
    try {
      // Save settings to localStorage or API
      localStorage.setItem('lucid-connection-settings', JSON.stringify(data))
      toast.success('Connection settings saved successfully')
    } catch (error) {
      toast.error('Failed to save connection settings')
      console.error('Settings save error:', error)
    }
  }

  const testConnection = async () => {
    try {
      const torClient = new TorClient()
      const health = await torClient.healthCheck()
      if (health) {
        toast.success('Connection test successful')
        checkTorStatus()
      } else {
        toast.error('Connection test failed')
      }
    } catch (error) {
      toast.error('Connection test failed')
      console.error('Connection test error:', error)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-lucid-text">Connection Settings</h2>
          <p className="text-lucid-text-secondary mt-1">
            Configure network and security settings for your RDP connections
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={checkTorStatus}
            disabled={isLoadingTorStatus}
            className="bg-lucid-primary text-white px-4 py-2 rounded-lg hover:bg-lucid-secondary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoadingTorStatus ? 'Checking...' : 'Test Connection'}
          </button>
        </div>
      </div>

      {/* Tor Status */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-lucid-text">Tor Connection Status</h3>
          <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-sm font-medium ${
            torStatus.connected
              ? 'bg-green-100 text-green-800'
              : 'bg-red-100 text-red-800'
          }`}>
            <div className={`w-2 h-2 rounded-full ${
              torStatus.connected ? 'bg-green-500' : 'bg-red-500'
            }`}></div>
            <span>{torStatus.connected ? 'Connected' : 'Disconnected'}</span>
          </div>
        </div>
        
        {torStatus.connected && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center space-x-3">
              <Globe className="w-5 h-5 text-lucid-text-secondary" />
              <div>
                <p className="text-sm font-medium text-lucid-text">Exit IP</p>
                <p className="text-sm text-lucid-text-secondary font-mono">{torStatus.ip}</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <Shield className="w-5 h-5 text-lucid-text-secondary" />
              <div>
                <p className="text-sm font-medium text-lucid-text">Exit Country</p>
                <p className="text-sm text-lucid-text-secondary">{torStatus.country}</p>
              </div>
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Network Settings */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center space-x-2 mb-4">
            <Wifi className="w-5 h-5 text-lucid-primary" />
            <h3 className="text-lg font-semibold text-lucid-text">Network Settings</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-lucid-text mb-2">
                Tor SOCKS Port
              </label>
              <input
                type="number"
                {...register('torSocksPort', { valueAsNumber: true })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-lucid-primary focus:border-lucid-primary"
                min="1"
                max="65535"
              />
              {errors.torSocksPort && (
                <p className="text-red-500 text-sm mt-1">{errors.torSocksPort.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-lucid-text mb-2">
                Tor Control Port
              </label>
              <input
                type="number"
                {...register('torControlPort', { valueAsNumber: true })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-lucid-primary focus:border-lucid-primary"
                min="1"
                max="65535"
              />
              {errors.torControlPort && (
                <p className="text-red-500 text-sm mt-1">{errors.torControlPort.message}</p>
              )}
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-lucid-text mb-2">
                API Base URL
              </label>
              <input
                type="url"
                {...register('apiBaseUrl')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-lucid-primary focus:border-lucid-primary"
                placeholder="https://sessions-gateway.onion"
              />
              {errors.apiBaseUrl && (
                <p className="text-red-500 text-sm mt-1">{errors.apiBaseUrl.message}</p>
              )}
            </div>
          </div>
        </div>

        {/* Connection Settings */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center space-x-2 mb-4">
            <Settings className="w-5 h-5 text-lucid-primary" />
            <h3 className="text-lg font-semibold text-lucid-text">Connection Settings</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-lucid-text mb-2">
                Connection Timeout (ms)
              </label>
              <input
                type="number"
                {...register('connectionTimeout', { valueAsNumber: true })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-lucid-primary focus:border-lucid-primary"
                min="1000"
                max="30000"
                step="1000"
              />
              {errors.connectionTimeout && (
                <p className="text-red-500 text-sm mt-1">{errors.connectionTimeout.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-lucid-text mb-2">
                Retry Attempts
              </label>
              <input
                type="number"
                {...register('retryAttempts', { valueAsNumber: true })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-lucid-primary focus:border-lucid-primary"
                min="1"
                max="10"
              />
              {errors.retryAttempts && (
                <p className="text-red-500 text-sm mt-1">{errors.retryAttempts.message}</p>
              )}
            </div>
          </div>
        </div>

        {/* Security Settings */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center space-x-2 mb-4">
            <Shield className="w-5 h-5 text-lucid-primary" />
            <h3 className="text-lg font-semibold text-lucid-text">Security Settings</h3>
          </div>
          
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <input
                type="checkbox"
                {...register('enableCompression')}
                className="w-4 h-4 text-lucid-primary border-gray-300 rounded focus:ring-lucid-primary"
              />
              <span className="text-lucid-text">Enable Compression</span>
            </div>

            <div className="flex items-center space-x-3">
              <input
                type="checkbox"
                {...register('enableEncryption')}
                className="w-4 h-4 text-lucid-primary border-gray-300 rounded focus:ring-lucid-primary"
              />
              <span className="text-lucid-text">Enable Encryption</span>
            </div>

            <div>
              <label className="block text-sm font-medium text-lucid-text mb-2">
                Log Level
              </label>
              <select
                {...register('logLevel')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-lucid-primary focus:border-lucid-primary"
              >
                <option value="debug">Debug</option>
                <option value="info">Info</option>
                <option value="warn">Warning</option>
                <option value="error">Error</option>
              </select>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isSubmitting}
            className="bg-lucid-primary text-white px-6 py-2 rounded-lg hover:bg-lucid-secondary transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            <Save className="w-4 h-4" />
            <span>{isSubmitting ? 'Saving...' : 'Save Settings'}</span>
          </button>
        </div>
      </form>
    </div>
  )
}
