'use client'

import { useState, useRef, useEffect } from 'react'
import { X, Camera, AlertCircle } from 'lucide-react'
import QRCode from 'qrcode-reader'

interface QRCodeScannerProps {
  onClose: () => void
  onScan: (data: any) => void
}

export function QRCodeScanner({ onClose, onScan }: QRCodeScannerProps) {
  const [isScanning, setIsScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [stream, setStream] = useState<MediaStream | null>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop())
      }
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [stream])

  const startScanning = async () => {
    try {
      setError(null)
      setIsScanning(true)

      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }
      })

      setStream(mediaStream)

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream
        videoRef.current.play()

        // Start QR code detection
        intervalRef.current = setInterval(() => {
          captureAndDecode()
        }, 1000)
      }
    } catch (err) {
      setError('Failed to access camera. Please ensure camera permissions are granted.')
      setIsScanning(false)
    }
  }

  const stopScanning = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      setStream(null)
    }
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    setIsScanning(false)
  }

  const captureAndDecode = () => {
    if (!videoRef.current || !canvasRef.current) return

    const video = videoRef.current
    const canvas = canvasRef.current
    const context = canvas.getContext('2d')

    if (!context) return

    // Set canvas dimensions to match video
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    // Draw video frame to canvas
    context.drawImage(video, 0, 0, canvas.width, canvas.height)

    // Get image data
    const imageData = context.getImageData(0, 0, canvas.width, canvas.height)

    // Create QR code reader
    const qr = new QRCode()

    qr.callback = (err: any, result: any) => {
      if (err) {
        // No QR code found, continue scanning
        return
      }

      if (result) {
        try {
          const sessionData = JSON.parse(result.result)
          stopScanning()
          onScan(sessionData)
        } catch (parseError) {
          setError('Invalid QR code format')
          console.error('QR code parse error:', parseError)
        }
      }
    }

    // Decode QR code
    qr.decode(imageData)
  }

  const handleClose = () => {
    stopScanning()
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b">
          <h3 className="text-lg font-semibold text-lucid-text">Scan QR Code</h3>
          <button
            onClick={handleClose}
            className="text-lucid-text-secondary hover:text-lucid-text transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2">
              <AlertCircle className="w-5 h-5 text-red-500" />
              <span className="text-red-700 text-sm">{error}</span>
            </div>
          )}

          {!isScanning ? (
            <div className="text-center">
              <div className="mx-auto w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                <Camera className="w-8 h-8 text-gray-400" />
              </div>
              <h4 className="text-lg font-medium text-lucid-text mb-2">Ready to Scan</h4>
              <p className="text-lucid-text-secondary mb-6">
                Position the QR code within the camera view to scan session information
              </p>
              <button
                onClick={startScanning}
                className="bg-lucid-primary text-white px-6 py-2 rounded-lg hover:bg-lucid-secondary transition-colors"
              >
                Start Scanning
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="relative bg-gray-100 rounded-lg overflow-hidden">
                <video
                  ref={videoRef}
                  className="w-full h-64 object-cover"
                  playsInline
                />
                <div className="absolute inset-0 border-2 border-lucid-primary rounded-lg pointer-events-none">
                  <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-lucid-primary"></div>
                  <div className="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 border-lucid-primary"></div>
                  <div className="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 border-lucid-primary"></div>
                  <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-lucid-primary"></div>
                </div>
              </div>

              <canvas
                ref={canvasRef}
                className="hidden"
              />

              <div className="text-center">
                <p className="text-sm text-lucid-text-secondary mb-4">
                  Position the QR code within the frame above
                </p>
                <button
                  onClick={stopScanning}
                  className="bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition-colors"
                >
                  Stop Scanning
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Instructions */}
        <div className="px-6 pb-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h5 className="font-medium text-blue-900 mb-2">How to use:</h5>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• Point your camera at a Lucid RDP session QR code</li>
              <li>• Ensure the QR code is clearly visible and well-lit</li>
              <li>• Hold steady until the code is automatically detected</li>
              <li>• Session details will be imported automatically</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
