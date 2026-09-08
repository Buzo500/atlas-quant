import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  async rewrites() {
    return {
      beforeFiles: [{ source: '/api/:path*', destination: 'http://127.0.0.1:8000/api/:path*' }],
      afterFiles: [],
      fallback: [],
    };
  },
};

export default nextConfig;
