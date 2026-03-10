'use client'

import { useState, useEffect } from 'react'
import { BootstrapWizard } from '@/components/BootstrapWizard'
import { ManifestsViewer } from '@/components/ManifestsViewer'
import { PayoutManager } from '@/components/PayoutManager'
import { KeyManager } from '@/components/KeyManager'
import { Diagnostics } from '@/components/Diagnostics'
import { OTAManager } from '@/components/OTAManager'
import { useAuthStore } from '@/stores/authStore'
import { TorClient } from '@/services/tor'

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const { isAuthenticated, user } = useAuthStore()
  const [torStatus, setTorStatus] = useState<boolean>(false)

  useEffect(() => {
    // Check Tor connectivity
    const checkTorStatus = async () => {
      try {
        const torClient = new TorClient()
        const status = await torClient.healthCheck()
        setTorStatus(status)
      } catch (error) {
        console.error('Tor connectivity check failed:', error)
        setTorStatus(false)
      }
    }

    checkTorStatus()
  }, [])

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-lucid-background flex items-center justify-center">
        <div className="bg-white p-8 rounded-lg shadow-lg max-w-md w-full">
          <h1 className="text-2xl font-bold text-center mb-6">Lucid Admin GUI</h1>
          <div className="text-center">
            <p className="text-lucid-text-secondary mb-4">
              Please authenticate to access admin functions
            </p>
            <button 
              onClick={() => window.location.href = '/auth'}
              className="bg-lucid-primary text-white px-6 py-2 rounded-lg hover:bg-lucid-secondary transition-colors"
            >
              Authenticate
            </button>
          </div>
        </div>
      </div>
    )
  }

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', component: Diagnostics },
    { id: 'bootstrap', label: 'Bootstrap', component: BootstrapWizard },
    { id: 'manifests', label: 'Manifests', component: ManifestsViewer },
    { id: 'payouts', label: 'Payouts', component: PayoutManager },
    { id: 'keys', label: 'Keys', component: KeyManager },
    { id: 'updates', label: 'Updates', component: OTAManager },
  ]

  const ActiveComponent = tabs.find(tab => tab.id === activeTab)?.component || Diagnostics

  return (
    <div className="min-h-screen bg-lucid-background">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-semibold text-lucid-text">Lucid Admin GUI</h1>
              <div className="ml-4 flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${torStatus ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className="text-sm text-lucid-text-secondary">
                  {torStatus ? 'Tor Connected' : 'Tor Disconnected'}
                </span>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-lucid-text-secondary">
                Admin: {user?.email}
              </span>
              <button 
                onClick={() => useAuthStore.getState().logout()}
                className="text-sm text-lucid-error hover:text-red-700"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-lucid-primary text-lucid-primary'
                    : 'border-transparent text-lucid-text-secondary hover:text-lucid-text hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ActiveComponent />
      </main>
    </div>
  )
}
