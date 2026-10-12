/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    // In local development, proxy /fastapi/* calls directly to FastAPI backend on port 8000
    const fastapiOrigin =
      process.env.FASTAPI_INTERNAL_URL || process.env.FASTAPI_URL || 'http://127.0.0.1:8000'
    return [
      {
        source: '/fastapi/:path*',
        destination: `${fastapiOrigin}/api/v1/:path*`,
      },
    ]
  },
}

export default nextConfig
