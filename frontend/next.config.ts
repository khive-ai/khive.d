import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Performance optimizations for Agentic ERP
  compiler: {
    removeConsole: process.env.NODE_ENV === "production",
  },

  experimental: {
    turbo: {
      rules: {
        "*.svg": {
          loaders: ["@svgr/webpack"],
          as: "*.js",
        },
      },
    },
    optimizeCss: true,
    memoryBasedWorkersCount: true,
  },

  // Image optimization
  images: {
    formats: ["image/webp", "image/avif"],
    minimumCacheTTL: 31536000, // 1 year cache
  },

  // Enhanced performance optimizations for Ocean's <100ms requirements
  webpack: (config, { dev, isServer }) => {
    if (!dev && !isServer) {
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          chunks: "all",
          minSize: 10000,
          maxSize: 250000,
          cacheGroups: {
            vendor: {
              test: /[\\/]node_modules[\\/]/,
              name: "vendors",
              chunks: "all",
              priority: 20,
            },
            mui: {
              test: /[\\/]node_modules[\\/]@mui[\\/]/,
              name: "mui",
              chunks: "all",
              priority: 30,
            },
            performance: {
              test: /[\\/]src[\\/](lib[\\/](utils|performance)|components[\\/]performance)[\\/]/,
              name: "performance",
              chunks: "all",
              priority: 40,
              enforce: true,
            },
            khiveCore: {
              test: /[\\/]src[\\/](components|lib|hooks)[\\/]/,
              name: "khive-core",
              chunks: "all",
              priority: 10,
              enforce: true,
            },
          },
        },
        moduleIds: 'deterministic',
        runtimeChunk: {
          name: 'runtime',
        },
      };
      
      // Add performance optimizations for Ocean's requirements
      config.resolve = {
        ...config.resolve,
        alias: {
          ...config.resolve.alias,
          // Optimize React for production
          'react': 'react/index.js',
          'react-dom': 'react-dom/index.js',
        }
      };
    }

    // Tree shaking optimization
    config.optimization = {
      ...config.optimization,
      usedExports: true,
      sideEffects: false,
    };
    
    return config;
  },

  // Security headers for ERP system
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "X-DNS-Prefetch-Control",
            value: "on",
          },
          {
            key: "Strict-Transport-Security",
            value: "max-age=63072000; includeSubDomains; preload",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "Referrer-Policy",
            value: "origin-when-cross-origin",
          },
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
        ],
      },
    ];
  },

  // ERP routing
  async redirects() {
    return [
      {
        source: "/",
        destination: "/command-center",
        permanent: false,
      },
    ];
  },

  eslint: {
    dirs: ["src", "app", "components", "lib"],
    ignoreDuringBuilds: false,
  },

  typescript: {
    ignoreBuildErrors: true,
  },

  output: "standalone",
  poweredByHeader: false,
};

export default nextConfig;