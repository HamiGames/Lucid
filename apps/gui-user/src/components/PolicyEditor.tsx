'use client'

import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Save, Eye, EyeOff, Shield } from 'lucide-react'
import { PolicyAPI } from '@/services/api'
import toast from 'react-hot-toast'

const policySchema = z.object({
  mouseEnabled: z.boolean(),
  keyboardEnabled: z.boolean(),
  clipboardEnabled: z.boolean(),
  fileTransferEnabled: z.boolean(),
  deviceRedirectEnabled: z.boolean(),
  audioEnabled: z.boolean(),
  videoEnabled: z.boolean(),
  privacyShieldEnabled: z.boolean(),
  maxBitrate: z.number().min(100).max(10000),
  compressionLevel: z.number().min(0).max(9),
  encryptionLevel: z.enum(['none', 'basic', 'standard', 'high']),
  sessionTimeout: z.number().min(5).max(480),
})

type PolicyFormData = z.infer<typeof policySchema>

interface PolicyPreset {
  name: string
  description: string
  settings: PolicyFormData
}

const policyPresets: PolicyPreset[] = [
  {
    name: 'Strict',
    description: 'Maximum security with minimal features',
    settings: {
      mouseEnabled: true,
      keyboardEnabled: true,
      clipboardEnabled: false,
      fileTransferEnabled: false,
      deviceRedirectEnabled: false,
      audioEnabled: false,
      videoEnabled: true,
      privacyShieldEnabled: true,
      maxBitrate: 1000,
      compressionLevel: 9,
      encryptionLevel: 'high',
      sessionTimeout: 30,
    }
  },
  {
    name: 'Standard',
    description: 'Balanced security and functionality',
    settings: {
      mouseEnabled: true,
      keyboardEnabled: true,
      clipboardEnabled: true,
      fileTransferEnabled: false,
      deviceRedirectEnabled: false,
      audioEnabled: false,
      videoEnabled: true,
      privacyShieldEnabled: true,
      maxBitrate: 2500,
      compressionLevel: 6,
      encryptionLevel: 'standard',
      sessionTimeout: 60,
    }
  },
  {
    name: 'Custom',
    description: 'Fully customizable settings',
    settings: {
      mouseEnabled: true,
      keyboardEnabled: true,
      clipboardEnabled: true,
      fileTransferEnabled: true,
      deviceRedirectEnabled: true,
      audioEnabled: true,
      videoEnabled: true,
      privacyShieldEnabled: false,
      maxBitrate: 5000,
      compressionLevel: 3,
      encryptionLevel: 'basic',
      sessionTimeout: 120,
    }
  }
]

export function PolicyEditor() {
  const [selectedPreset, setSelectedPreset] = useState<string>('Standard')
  const [showAdvanced, setShowAdvanced] = useState(false)

  const { register, handleSubmit, watch, setValue, formState: { errors, isSubmitting } } = useForm<PolicyFormData>({
    resolver: zodResolver(policySchema),
    defaultValues: policyPresets[1].settings // Default to Standard preset
  })

  const watchedValues = watch()

  useEffect(() => {
    const preset = policyPresets.find(p => p.name === selectedPreset)
    if (preset) {
      Object.entries(preset.settings).forEach(([key, value]) => {
        setValue(key as keyof PolicyFormData, value)
      })
    }
  }, [selectedPreset, setValue])

  const onSubmit = async (data: PolicyFormData) => {
    try {
      await PolicyAPI.updatePolicy(data)
      toast.success('Policy updated successfully')
    } catch (error) {
      toast.error('Failed to update policy')
      console.error('Policy update error:', error)
    }
  }

  const handlePresetChange = (presetName: string) => {
    setSelectedPreset(presetName)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-lucid-text">Session Policy</h2>
          <p className="text-lucid-text-secondary mt-1">
            Configure security and functionality settings for your RDP sessions
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Shield className="w-5 h-5 text-lucid-primary" />
          <span className="text-sm font-medium text-lucid-text">Policy Active</span>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Policy Presets */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold text-lucid-text mb-4">Policy Presets</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {policyPresets.map((preset) => (
              <div
                key={preset.name}
                className={`p-4 rounded-lg border-2 cursor-pointer transition-colors ${
                  selectedPreset === preset.name
                    ? 'border-lucid-primary bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => handlePresetChange(preset.name)}
              >
                <h4 className="font-semibold text-lucid-text">{preset.name}</h4>
                <p className="text-sm text-lucid-text-secondary mt-1">{preset.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Basic Settings */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold text-lucid-text mb-4">Basic Settings</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <label className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  {...register('mouseEnabled')}
                  className="w-4 h-4 text-lucid-primary border-gray-300 rounded focus:ring-lucid-primary"
                />
                <span className="text-lucid-text">Enable Mouse Input</span>
              </label>

              <label className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  {...register('keyboardEnabled')}
                  className="w-4 h-4 text-lucid-primary border-gray-300 rounded focus:ring-lucid-primary"
                />
                <span className="text-lucid-text">Enable Keyboard Input</span>
              </label>

              <label className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  {...register('clipboardEnabled')}
                  className="w-4 h-4 text-lucid-primary border-gray-300 rounded focus:ring-lucid-primary"
                />
                <span className="text-lucid-text">Enable Clipboard Sharing</span>
              </label>

              <label className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  {...register('fileTransferEnabled')}
                  className="w-4 h-4 text-lucid-primary border-gray-300 rounded focus:ring-lucid-primary"
                />
                <span className="text-lucid-text">Enable File Transfer</span>
              </label>
            </div>

            <div className="space-y-4">
              <label className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  {...register('deviceRedirectEnabled')}
                  className="w-4 h-4 text-lucid-primary border-gray-300 rounded focus:ring-lucid-primary"
                />
                <span className="text-lucid-text">Enable Device Redirection</span>
              </label>

              <label className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  {...register('audioEnabled')}
                  className="w-4 h-4 text-lucid-primary border-gray-300 rounded focus:ring-lucid-primary"
                />
                <span className="text-lucid-text">Enable Audio</span>
              </label>

              <label className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  {...register('videoEnabled')}
                  className="w-4 h-4 text-lucid-primary border-gray-300 rounded focus:ring-lucid-primary"
                />
                <span className="text-lucid-text">Enable Video</span>
              </label>

              <label className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  {...register('privacyShieldEnabled')}
                  className="w-4 h-4 text-lucid-primary border-gray-300 rounded focus:ring-lucid-primary"
                />
                <span className="text-lucid-text">Enable Privacy Shield</span>
              </label>
            </div>
          </div>
        </div>

        {/* Advanced Settings */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-lucid-text">Advanced Settings</h3>
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center space-x-2 text-lucid-primary hover:text-lucid-secondary"
            >
              {showAdvanced ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              <span>{showAdvanced ? 'Hide' : 'Show'} Advanced</span>
            </button>
          </div>

          {showAdvanced && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-lucid-text mb-2">
                    Max Bitrate (kbps)
                  </label>
                  <input
                    type="number"
                    {...register('maxBitrate', { valueAsNumber: true })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-lucid-primary focus:border-lucid-primary"
                    min="100"
                    max="10000"
                    step="100"
                  />
                  {errors.maxBitrate && (
                    <p className="text-red-500 text-sm mt-1">{errors.maxBitrate.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-lucid-text mb-2">
                    Compression Level
                  </label>
                  <input
                    type="range"
                    {...register('compressionLevel', { valueAsNumber: true })}
                    className="w-full"
                    min="0"
                    max="9"
                  />
                  <div className="flex justify-between text-xs text-lucid-text-secondary mt-1">
                    <span>Fast</span>
                    <span>{watchedValues.compressionLevel || 6}</span>
                    <span>Small</span>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-lucid-text mb-2">
                    Encryption Level
                  </label>
                  <select
                    {...register('encryptionLevel')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-lucid-primary focus:border-lucid-primary"
                  >
                    <option value="none">None</option>
                    <option value="basic">Basic</option>
                    <option value="standard">Standard</option>
                    <option value="high">High</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-lucid-text mb-2">
                    Session Timeout (minutes)
                  </label>
                  <input
                    type="number"
                    {...register('sessionTimeout', { valueAsNumber: true })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-lucid-primary focus:border-lucid-primary"
                    min="5"
                    max="480"
                  />
                  {errors.sessionTimeout && (
                    <p className="text-red-500 text-sm mt-1">{errors.sessionTimeout.message}</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isSubmitting}
            className="bg-lucid-primary text-white px-6 py-2 rounded-lg hover:bg-lucid-secondary transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            <Save className="w-4 h-4" />
            <span>{isSubmitting ? 'Saving...' : 'Save Policy'}</span>
          </button>
        </div>
      </form>
    </div>
  )
}
