import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Performance optimizations inspired by rust-performance principles
  compiler: {
    // Remove console logs in production (zero-cost abstraction)
    removeConsole: process.env.NODE_ENV === 'production',
  },

  // Experimental features for better performance
  experimental: {
    // Use Turbopack for faster builds
    turbo: {
      rules: {
        '*.svg': {
          loaders: ['@svgr/webpack'],
          as: '*.js',
        },
      },
    },
    // Optimize CSS loading
    optimizeCss: true,
    // Enable memory optimization
    memoryBasedWorkersCount: true,
  },

  // Image optimization
  images: {
    formats: ['image/webp', 'image/avif'],
    minimumCacheTTL: 31536000, // 1 year cache
  },

  // Bundle analyzer in development
  webpack: (config, { dev, isServer }) => {
    // Performance optimizations
    if (!dev && !isServer) {
      // Split chunks for better caching (similar to monomorphization control)
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          chunks: 'all',
          cacheGroups: {
            vendor: {
              test: /[\\/]node_modules[\\/]/,
              name: 'vendors',
              chunks: 'all',
            },
            mui: {
              test: /[\\/]node_modules[\\/]@mui[\\/]/,
              name: 'mui',
              chunks: 'all',
            },
            common: {
              name: 'common',
              minChunks: 2,
              chunks: 'all',
              enforce: true,
            },
          },
        },
      };
    }

    return config;
  },

  // Environment variables
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },

  // Headers for performance and security
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on',
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin',
          },
        ],
      },
    ];
  },

  // Redirects for clean URLs and dashboard navigation
  async redirects() {
    return [
      {
        source: '/home',
        destination: '/',
        permanent: true,
      },
      {
        source: '/dashboard',
        destination: '/dashboard/sessions',
        permanent: false,
      },
    ];
  },
  
  // ESLint configuration for build
  eslint: {
    dirs: ['src', 'app', 'components', 'lib'],
    ignoreDuringBuilds: false,
  },
  
  // TypeScript configuration for build
  typescript: {
    ignoreBuildErrors: false,
  },
  
  // Output configuration for deployment
  output: 'standalone',
  
  // Disable x-powered-by header
  poweredByHeader: false,
};

export default nextConfig;
