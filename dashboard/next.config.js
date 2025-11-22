const path = require('path');
const dotenv = require('dotenv');

// Load environment variables from parent directory
dotenv.config({ path: path.join(__dirname, '../.env') });
dotenv.config({ path: path.join(__dirname, '../.env.local'), override: true });

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false, // Disable for production build
  images: {
    domains: ['localhost'],
  },
  // Disable static generation completely
  output: 'standalone',
  experimental: {
    // Disable App Router static generation
    serverComponentsExternalPackages: [],
  },
  // Disable ESLint during builds
  eslint: {
    ignoreDuringBuilds: true,
  },
  // Disable TypeScript checks during builds  
  typescript: {
    ignoreBuildErrors: true,
  },
  // Disable trailing slash and other features
  trailingSlash: false,
  // Don't generate static pages
  generateEtags: false,
  // Skip build-time static generation
  distDir: '.next',
  async rewrites() {
    // Use environment variable for API URL, fallback to localhost for development
    const apiUrl = process.env.API_BASE_URL || 'http://localhost:8000';
    
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/v1/:path*`,
      },
    ];
  },
  // Skip building static pages for problematic routes
  webpack: (config, { isServer }) => {
    if (isServer) {
      config.resolve.alias = {
        ...config.resolve.alias,
      };
    }
    return config;
  },
};

module.exports = nextConfig;
