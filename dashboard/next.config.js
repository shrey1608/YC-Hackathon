/** @type {import('next').NextConfig} */

// All browser calls hit /api/* on the Next origin and are proxied to the
// FastAPI control-plane. This keeps the live WebRTC signaling (/api/offer)
// same-origin so there are no CORS preflights on the SDP exchange.
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` },
      { source: "/health", destination: `${BACKEND_URL}/health` },
    ];
  },
};

module.exports = nextConfig;
