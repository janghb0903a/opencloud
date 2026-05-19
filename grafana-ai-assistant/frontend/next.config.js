/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    optimizePackageImports: ["framer-motion"]
  },
  async rewrites() {
    const backend = process.env.BACKEND_INTERNAL_URL || "http://backend:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backend}/api/:path*`
      },
      {
        source: "/healthz",
        destination: `${backend}/healthz`
      }
    ];
  }
};

module.exports = nextConfig;