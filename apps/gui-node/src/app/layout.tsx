import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Lucid Node GUI',
  description: 'Node management interface for Lucid RDP',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
