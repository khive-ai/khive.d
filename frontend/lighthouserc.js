module.exports = {
  ci: {
    collect: {
      url: ['http://localhost:3000'],
      startServerCommand: 'npm run start',
      startServerReadyPattern: 'Ready on',
      startServerReadyTimeout: 60000,
    },
    assert: {
      // Performance thresholds inspired by rust-performance principles
      assertions: {
        'categories:performance': ['error', { minScore: 0.8 }],
        'categories:accessibility': ['error', { minScore: 0.9 }],
        'categories:best-practices': ['error', { minScore: 0.85 }],
        'categories:seo': ['error', { minScore: 0.9 }],
        
        // Core Web Vitals
        'first-contentful-paint': ['error', { maxNumericValue: 2000 }],
        'largest-contentful-paint': ['error', { maxNumericValue: 2500 }],
        'cumulative-layout-shift': ['error', { maxNumericValue: 0.1 }],
        'total-blocking-time': ['error', { maxNumericValue: 300 }],
        
        // Resource efficiency
        'unused-javascript': ['warn', { maxNumericValue: 0.2 }],
        'unused-css-rules': ['warn', { maxNumericValue: 0.2 }],
        'modern-image-formats': 'error',
        'uses-text-compression': 'error',
        
        // Security
        'is-on-https': 'off', // Allow for local testing
        'uses-http2': 'warn',
      },
    },
    upload: {
      target: 'temporary-public-storage',
    },
  },
};