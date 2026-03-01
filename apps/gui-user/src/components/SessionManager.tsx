'use client'

import { useState, useEffect } from 'react'
import { useQuery } from 'react-query'
import { Play, Square, RotateCcw, Plus, QrCode } from 'lucide-react'
import { SessionAPI } from '@/services/api'
import { QRCodeScanner } from './QRCodeScanner'
import toast from 'react-hot-toast'

interface Session {
  id: string
  name: string
  status: 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'failed'
  host: string
  port: number
  createdAt: string
  lastConnected?: string
}

export function SessionManager() {
  const [showQRScanner, setShowQRScanner] = useState(false)
  const [selectedSession, setSelectedSession] = useState<Session | null>(null)

  const { data: sessions, isLoading, refetch } = useQuery(
    'sessions',
    SessionAPI.getSessions,
    {
      refetchInterval: 5000, // Poll every 5 seconds
    }
  )

  const handleConnect = async (sessionId: string) => {
    try {
      await SessionAPI.connect(sessionId)
      toast.success('Connecting to session...')
      refetch()
    } catch (error) {
      toast.error('Failed to connect to session')
      console.error('Connection error:', error)
    }
  }

  const handleDisconnect = async (sessionId: string) => {
    try {
      await SessionAPI.disconnect(sessionId)
      toast.success('Disconnected from session')
      refetch()
    } catch (error) {
      toast.error('Failed to disconnect from session')
      console.error('Disconnect error:', error)
    }
  }

  const handleReconnect = async (sessionId: string) => {
    try {
      await SessionAPI.reconnect(sessionId)
      toast.success('Reconnecting to session...')
      refetch()
    } catch (error) {
      toast.error('Failed to reconnect to session')
      console.error('Reconnect error:', error)
    }
  }

  const getStatusColor = (status: Session['status']) => {
    switch (status) {
      case 'connected':
        return 'bg-green-100 text-green-800'
      case 'connecting':
      case 'reconnecting':
        return 'bg-yellow-100 text-yellow-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusIcon = (status: Session['status']) => {
    switch (status) {
      case 'connected':
        return <Play className="w-4 h-4" />
      case 'connecting':
      case 'reconnecting':
        return <RotateCcw className="w-4 h-4" />
      case 'failed':
        return <Square className="w-4 h-4" />
      default:
        return <Square className="w-4 h-4" />
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-lucid-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-lucid-text">Session Management</h2>
          <p className="text-lucid-text-secondary mt-1">
            Manage your RDP sessions and connections
          </p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={() => setShowQRScanner(true)}
            className="bg-lucid-primary text-white px-4 py-2 rounded-lg hover:bg-lucid-secondary transition-colors flex items-center space-x-2"
          >
            <QrCode className="w-4 h-4" />
            <span>Scan QR</span>
          </button>
          <button className="bg-lucid-accent text-white px-4 py-2 rounded-lg hover:bg-yellow-600 transition-colors flex items-center space-x-2">
            <Plus className="w-4 h-4" />
            <span>New Session</span>
          </button>
        </div>
      </div>

      {/* Sessions Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {sessions?.map((session) => (
          <div
            key={session.id}
            className="bg-white rounded-lg shadow-sm border p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="font-semibold text-lucid-text">{session.name}</h3>
                <p className="text-sm text-lucid-text-secondary">
                  {session.host}:{session.port}
                </p>
              </div>
              <span className={`px-2 py-1 rounded-full text-xs font-medium flex items-center space-x-1 ${getStatusColor(session.status)}`}>
                {getStatusIcon(session.status)}
                <span className="capitalize">{session.status}</span>
              </span>
            </div>

            <div className="text-sm text-lucid-text-secondary mb-4">
              <p>Created: {new Date(session.createdAt).toLocaleDateString()}</p>
              {session.lastConnected && (
                <p>Last connected: {new Date(session.lastConnected).toLocaleString()}</p>
              )}
            </div>

            <div className="flex space-x-2">
              {session.status === 'disconnected' || session.status === 'failed' ? (
                <button
                  onClick={() => handleConnect(session.id)}
                  className="flex-1 bg-lucid-primary text-white px-3 py-2 rounded text-sm hover:bg-lucid-secondary transition-colors flex items-center justify-center space-x-1"
                >
                  <Play className="w-4 h-4" />
                  <span>Connect</span>
                </button>
              ) : (
                <button
                  onClick={() => handleDisconnect(session.id)}
                  className="flex-1 bg-red-500 text-white px-3 py-2 rounded text-sm hover:bg-red-600 transition-colors flex items-center justify-center space-x-1"
                >
                  <Square className="w-4 h-4" />
                  <span>Disconnect</span>
                </button>
              )}
              
              {(session.status === 'failed' || session.status === 'disconnected') && (
                <button
                  onClick={() => handleReconnect(session.id)}
                  className="bg-lucid-accent text-white px-3 py-2 rounded text-sm hover:bg-yellow-600 transition-colors flex items-center justify-center space-x-1"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {sessions?.length === 0 && (
        <div className="text-center py-12">
          <div className="mx-auto w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-4">
            <Play className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-medium text-lucid-text mb-2">No sessions found</h3>
          <p className="text-lucid-text-secondary mb-4">
            Create a new session or scan a QR code to get started
          </p>
          <button className="bg-lucid-primary text-white px-6 py-2 rounded-lg hover:bg-lucid-secondary transition-colors">
            Create New Session
          </button>
        </div>
      )}

      {/* QR Code Scanner Modal */}
      {showQRScanner && (
        <QRCodeScanner
          onClose={() => setShowQRScanner(false)}
          onScan={(sessionData) => {
            console.log('Scanned session data:', sessionData)
            setShowQRScanner(false)
            toast.success('Session data scanned successfully')
          }}
        />
      )}
    </div>
  )
}
