'use client'

import { useState } from 'react'
import { useQuery } from 'react-query'
import { Download, Eye, Calendar, Hash, FileText } from 'lucide-react'
import { ProofsAPI } from '@/services/api'
import toast from 'react-hot-toast'

export function ProofsViewer() {
  const [selectedProof, setSelectedProof] = useState<string | null>(null)
  const [exportFormat, setExportFormat] = useState<'json' | 'pdf'>('json')

  const { data: proofs, isLoading } = useQuery(
    'proofs',
    ProofsAPI.getProofs,
    {
      refetchInterval: 10000, // Poll every 10 seconds
    }
  )

  const handleExport = async (proofId: string) => {
    try {
      const blob = await ProofsAPI.exportProof(proofId, exportFormat)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `proof-${proofId}.${exportFormat}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      toast.success(`Proof exported as ${exportFormat.toUpperCase()}`)
    } catch (error) {
      toast.error('Failed to export proof')
      console.error('Export error:', error)
    }
  }

  const getProofTypeColor = (type: string) => {
    switch (type) {
      case 'connection':
        return 'bg-green-100 text-green-800'
      case 'activity':
        return 'bg-blue-100 text-blue-800'
      case 'disconnection':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
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
          <h2 className="text-2xl font-bold text-lucid-text">Proofs Viewer</h2>
          <p className="text-lucid-text-secondary mt-1">
            View and export session proofs and audit trails
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <select
            value={exportFormat}
            onChange={(e) => setExportFormat(e.target.value as 'json' | 'pdf')}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-lucid-primary focus:border-lucid-primary"
          >
            <option value="json">Export as JSON</option>
            <option value="pdf">Export as PDF</option>
          </select>
        </div>
      </div>

      {/* Proofs List */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="p-6">
          <h3 className="text-lg font-semibold text-lucid-text mb-4">Session Proofs</h3>
          
          {proofs?.length === 0 ? (
            <div className="text-center py-12">
              <div className="mx-auto w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                <FileText className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium text-lucid-text mb-2">No proofs found</h3>
              <p className="text-lucid-text-secondary">
                Proofs will appear here as you use RDP sessions
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {proofs?.map((proof) => (
                <div
                  key={proof.id}
                  className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                    selectedProof === proof.id
                      ? 'border-lucid-primary bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => setSelectedProof(
                    selectedProof === proof.id ? null : proof.id
                  )}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getProofTypeColor(proof.type)}`}>
                          {proof.type}
                        </span>
                        <span className="text-sm text-lucid-text-secondary">
                          Session: {proof.sessionId}
                        </span>
                      </div>
                      
                      <div className="flex items-center space-x-4 text-sm text-lucid-text-secondary">
                        <div className="flex items-center space-x-1">
                          <Calendar className="w-4 h-4" />
                          <span>{formatTimestamp(proof.timestamp)}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <Hash className="w-4 h-4" />
                          <span className="font-mono">{proof.hash.substring(0, 8)}...</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleExport(proof.id)
                        }}
                        className="p-2 text-lucid-text-secondary hover:text-lucid-primary transition-colors"
                        title="Export proof"
                      >
                        <Download className="w-4 h-4" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedProof(
                            selectedProof === proof.id ? null : proof.id
                          )
                        }}
                        className="p-2 text-lucid-text-secondary hover:text-lucid-primary transition-colors"
                        title="View details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Proof Details */}
                  {selectedProof === proof.id && (
                    <div className="mt-4 pt-4 border-t border-gray-200">
                      <h4 className="font-medium text-lucid-text mb-2">Proof Data</h4>
                      <pre className="bg-gray-50 p-3 rounded text-xs overflow-x-auto">
                        {JSON.stringify(proof.data, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Summary Stats */}
      {proofs && proofs.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center">
              <div className="p-2 bg-green-100 rounded-lg">
                <FileText className="w-6 h-6 text-green-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-lucid-text-secondary">Total Proofs</p>
                <p className="text-2xl font-bold text-lucid-text">{proofs.length}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Calendar className="w-6 h-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-lucid-text-secondary">This Week</p>
                <p className="text-2xl font-bold text-lucid-text">
                  {proofs.filter(p => {
                    const proofDate = new Date(p.timestamp)
                    const weekAgo = new Date()
                    weekAgo.setDate(weekAgo.getDate() - 7)
                    return proofDate >= weekAgo
                  }).length}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <Hash className="w-6 h-6 text-yellow-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-lucid-text-secondary">Unique Sessions</p>
                <p className="text-2xl font-bold text-lucid-text">
                  {new Set(proofs.map(p => p.sessionId)).size}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
