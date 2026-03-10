/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  experimental: {
    serverComponentsExternalPackages: ['sharp', 'ws']
  },
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
    TOR_SOCKS_PORT: process.env.TOR_SOCKS_PORT || '9050',
    TOR_CONTROL_PORT: process.env.TOR_CONTROL_PORT || '9051',
    API_BASE_URL: process.env.API_BASE_URL || 'https://tron-payment-service.onion',
    BLOCKCHAIN_RPC_URL: process.env.BLOCKCHAIN_RPC_URL,
    TRON_RPC_URL: process.env.TRON_RPC_URL,
    MONGO_URL: process.env.MONGO_URL
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.API_BASE_URL || 'https://tron-payment-service.onion'}/api/:path*`
      }
    ]
  },
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
        crypto: false,
      }
    }
    return config
  }
}

module.exports = nextConfig
