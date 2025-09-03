# Khive Frontend

A high-performance Next.js application built with TypeScript, optimized for
scalability and developer experience. This project implements rust-performance
inspired optimization principles and comprehensive monitoring.

## 🚀 Features

- **Next.js 15.5** with App Router and Turbopack for ultra-fast builds
- **TypeScript 5** with strict configuration for type safety
- **Material-UI v7** with Emotion for component styling
- **TailwindCSS v4** for utility-first styling
- **Comprehensive Testing** with Jest, Testing Library, and Playwright
- **Performance Monitoring** with Core Web Vitals tracking
- **CI/CD Pipeline** with GitHub Actions
- **Docker Support** for containerized deployment
- **Enhanced ESLint** configuration with performance-focused rules

## 📁 Project Structure

```
src/
├── app/                    # Next.js App Router
│   ├── api/               # API routes
│   ├── dashboard/         # Dashboard pages
│   ├── coordination/      # Coordination interface
│   └── ...
├── components/            # Reusable UI components
│   ├── ui/               # Base UI components
│   ├── charts/           # Chart components
│   └── forms/            # Form components
├── lib/                  # Core utilities and configurations
│   ├── api/              # API utilities
│   ├── hooks/            # Custom React hooks
│   ├── providers/        # Context providers
│   ├── stores/           # State management
│   ├── types/            # TypeScript type definitions
│   └── utils/            # Utility functions
└── styles/               # Global styles
```

## 🛠️ Getting Started

### Prerequisites

- Node.js 20+
- npm or yarn

### Installation

1. Clone the repository
2. Install dependencies:

```bash
npm install
```

3. Copy environment variables:

```bash
cp .env.example .env.local
```

4. Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to see the application.

## 📝 Available Scripts

### Development

- `npm run dev` - Start development server with Turbopack
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run type-check` - Run TypeScript type checking

### Code Quality

- `npm run lint` - Run ESLint
- `npm run lint:fix` - Fix ESLint issues automatically
- `npm run format` - Format code with Prettier
- `npm run format:check` - Check code formatting

### Testing

- `npm run test` - Run unit tests
- `npm run test:watch` - Run tests in watch mode
- `npm run test:coverage` - Run tests with coverage report
- `npm run test:ci` - Run tests for CI environment
- `npm run test:e2e` - Run Playwright E2E tests
- `npm run test:e2e:ui` - Run E2E tests with UI mode

### Performance

- `npm run analyze` - Analyze bundle size

## 🏗️ Architecture

### Performance Optimizations

The project implements several rust-performance inspired optimizations:

1. **Zero-Cost Abstractions**: Performance monitoring only activates when needed
2. **Memory Optimization**: Efficient resource loading and cleanup
3. **Bundle Splitting**: Intelligent code splitting for optimal caching
4. **Image Optimization**: WebP/AVIF support with proper caching
5. **Core Web Vitals**: Comprehensive performance monitoring

### Key Components

- **PerformanceProvider**: Centralized performance monitoring
- **usePerformance**: Hook for component-level performance tracking
- **Performance Utils**: Utilities for measuring and optimizing performance

## 🧪 Testing

### Unit Testing

Uses Jest with React Testing Library for comprehensive component testing:

```bash
npm run test
```

### E2E Testing

Playwright for end-to-end testing across multiple browsers:

```bash
npm run test:e2e
```

### Performance Testing

Lighthouse CI for automated performance monitoring in CI/CD.

## 🐳 Docker

### Development

```bash
docker-compose up frontend-dev --profile dev
```

### Production

```bash
docker-compose up frontend
```

## 🚀 Deployment

### CI/CD Pipeline

The project includes a comprehensive GitHub Actions workflow:

1. **Lint & Type Check**: Code quality validation
2. **Unit Tests**: Comprehensive test suite execution
3. **Build**: Production build creation
4. **E2E Tests**: Cross-browser testing
5. **Performance Audit**: Lighthouse performance checks
6. **Security Scan**: Dependency vulnerability scanning
7. **Deploy**: Automated deployment to staging/production

### Environment Configuration

Required environment variables:

```env
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
```

Optional for enhanced features:

```env
VERCEL_TOKEN=your_token_here
VERCEL_ORG_ID=your_org_id
VERCEL_PROJECT_ID=your_project_id
SNYK_TOKEN=your_snyk_token
LHCI_GITHUB_APP_TOKEN=your_lighthouse_token
```

## 🎯 Performance Monitoring

### Core Web Vitals Tracking

The application automatically tracks:

- **FCP** (First Contentful Paint) - Target: <1.5s
- **LCP** (Largest Contentful Paint) - Target: <2.5s
- **CLS** (Cumulative Layout Shift) - Target: <0.1
- **FID** (First Input Delay) - Target: <100ms

### Development Monitor

In development mode, a real-time performance monitor appears in the bottom-right
corner showing current metrics and budget violations.

### Performance Budget

Default performance budgets are configured with rust-performance principles:

```typescript
const performanceBudget = {
  fcp: 1500, // 1.5s
  lcp: 2500, // 2.5s
  cls: 0.1, // 0.1
  fid: 100, // 100ms
};
```

## 🔧 Configuration

### TypeScript

Strict TypeScript configuration with enhanced checks for better performance:

- `noUnusedLocals` - Prevent unused variables
- `noUnusedParameters` - Prevent unused parameters
- `exactOptionalPropertyTypes` - Strict optional properties
- `noUncheckedIndexedAccess` - Safe array/object access

### ESLint

Comprehensive ESLint configuration with performance-focused rules:

- Import optimization and ordering
- React performance patterns
- TypeScript best practices
- Accessibility checks
- Next.js optimizations

## 🏥 Health Checks

The application includes a health check endpoint at `/api/health` that provides:

- Application status
- System information
- Memory usage
- Uptime statistics

## 📈 Bundle Analysis

Use the analyze script to understand your bundle size:

```bash
npm run analyze
```

## 🤝 Contributing

1. Follow the established code style (Prettier + ESLint)
2. Write tests for new features
3. Ensure performance budgets are met
4. Update documentation as needed

## 🔒 Security

The project includes several security measures:

- Dependency vulnerability scanning with Snyk
- Security headers configuration
- Content Security Policy
- Safe TypeScript patterns

---

Built with ❤️ using Next.js and performance-first principles.
