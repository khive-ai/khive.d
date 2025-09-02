# Frontend Development Guide

## Getting Started

### Prerequisites
- Node.js 18.x or 20.x
- npm 9.x or later
- Git

### Installation
```bash
cd frontend
npm install
```

### Development Server
```bash
npm run dev
```

The application will be available at `http://localhost:3000`.

## Project Structure

```
frontend/
├── .github/workflows/          # CI/CD pipeline configuration
├── public/                     # Static assets
├── src/                        # Source code
│   ├── app/                    # Next.js App Router
│   │   ├── (dashboard)/        # Dashboard route group
│   │   ├── api/               # API routes
│   │   ├── globals.css        # Global styles
│   │   ├── layout.tsx         # Root layout
│   │   └── page.tsx           # Landing page
│   ├── components/            # Component library
│   │   ├── ui/               # Base UI components
│   │   ├── feature/          # Feature-specific components
│   │   └── layout/           # Layout components
│   ├── lib/                   # Shared utilities and configuration
│   │   ├── api/              # API client and queries
│   │   ├── hooks/            # Custom React hooks
│   │   ├── types/            # TypeScript type definitions
│   │   ├── utils/            # Utility functions
│   │   ├── constants/        # Application constants
│   │   ├── stores/           # Client-side stores
│   │   └── config/           # Configuration files
│   ├── styles/               # Additional styling files
│   └── __tests__/            # Test files
├── .env.example               # Environment variables template
├── ARCHITECTURE.md            # Architecture documentation
├── DEVELOPMENT.md             # This file
├── jest.config.js             # Jest configuration
├── next.config.ts             # Next.js configuration
├── package.json               # Dependencies and scripts
├── tsconfig.json              # TypeScript configuration
└── README.md                  # Project overview
```

## Development Workflow

### 1. Creating New Features

1. **Create a new branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Follow the component architecture**:
   - UI components go in `src/components/ui/`
   - Feature-specific components go in `src/components/feature/`
   - Layout components go in `src/components/layout/`

3. **Use TypeScript**:
   - All files should use `.ts` or `.tsx` extensions
   - Define proper interfaces and types
   - Leverage path aliases: `@/components`, `@/lib`, etc.

4. **Write tests**:
   - Unit tests for components: `*.test.tsx`
   - Integration tests for features: `*.spec.tsx`
   - E2E tests using Playwright

### 2. Code Quality Standards

#### TypeScript
- Use strict mode (already configured)
- Define explicit return types for functions
- Use proper generics for reusable components
- Avoid `any` types

#### React Best Practices
- Use functional components with hooks
- Implement proper error boundaries
- Use React.memo for performance optimization when needed
- Follow the single responsibility principle

#### Styling
- Use Material-UI for primary components
- Use Tailwind CSS for utility styling
- Follow the design system patterns
- Use the `cn()` utility for conditional classes

### 3. State Management

#### Server State (API Data)
- Use TanStack React Query for all server interactions
- Follow the established query key patterns
- Implement optimistic updates where appropriate
- Handle loading and error states consistently

#### Client State
- Use React useState/useReducer for local component state
- Use custom hooks for shared logic
- Leverage Context API for deeply nested prop drilling scenarios

#### Form State
- Use React Hook Form for all forms
- Implement proper validation with TypeScript
- Handle async validation for API calls

### 4. API Integration

#### Making API Calls
```typescript
import { useSessionsQuery } from '@/api';

function SessionsList() {
  const { data: sessions, isLoading, error } = useSessionsQuery();
  
  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  
  return (
    <div>
      {sessions?.map(session => (
        <SessionCard key={session.id} session={session} />
      ))}
    </div>
  );
}
```

#### Error Handling
- Use the centralized error handling from the API client
- Display user-friendly error messages
- Implement retry mechanisms where appropriate
- Log errors for debugging

### 5. Testing Strategy

#### Unit Tests
```bash
npm run test          # Watch mode
npm run test:ci       # CI mode with coverage
```

#### E2E Tests
```bash
npm run test:e2e      # Run E2E tests
npm run test:e2e:ui   # Run with UI
```

#### Test Structure
```typescript
import { render, screen } from '@testing-library/react';
import { SessionMonitor } from '../session-monitor';

describe('SessionMonitor', () => {
  it('displays session information correctly', () => {
    const session = mockSession();
    render(<SessionMonitor session={session} />);
    
    expect(screen.getByText(session.objective)).toBeInTheDocument();
  });
});
```

## Available Scripts

```bash
# Development
npm run dev                # Start development server
npm run build             # Build for production
npm run start             # Start production server

# Code Quality
npm run lint              # Lint and fix code
npm run lint:check        # Check linting without fixing
npm run type-check        # Run TypeScript checks
npm run format            # Format code with Prettier
npm run format:check      # Check formatting

# Testing
npm run test              # Run tests in watch mode
npm run test:ci           # Run tests with coverage
npm run test:e2e          # Run E2E tests
npm run test:e2e:ui       # Run E2E tests with UI

# Utilities
npm run security:check    # Check for security vulnerabilities
npm run analyze           # Analyze bundle size
npm run clean             # Clean build cache
```

## Environment Variables

Create a `.env.local` file in the frontend directory:

```env
# API Configuration
NEXT_PUBLIC_API_BASE_URL=http://localhost:3001/api
NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:3001

# Application Configuration
NEXT_PUBLIC_APP_NAME=Khive Dashboard
NEXT_PUBLIC_APP_VERSION=0.1.0

# Feature Flags
NEXT_PUBLIC_ENABLE_DEBUG=true
NEXT_PUBLIC_ENABLE_ANALYTICS=false
```

## Component Development Patterns

### UI Components
Create reusable, accessible UI components:

```typescript
// src/components/ui/button.tsx
export interface ButtonProps {
  variant?: 'default' | 'destructive' | 'outline';
  size?: 'sm' | 'default' | 'lg';
  loading?: boolean;
  children: React.ReactNode;
}

export const Button = ({ variant = 'default', ...props }) => {
  // Implementation
};
```

### Feature Components
Build domain-specific components:

```typescript
// src/components/feature/session-monitor.tsx
export interface SessionMonitorProps {
  session: Session;
  onAction?: (action: string) => void;
}

export const SessionMonitor = ({ session, onAction }) => {
  // Implementation
};
```

## Performance Guidelines

### Bundle Optimization
- Use dynamic imports for large components
- Implement code splitting at route level
- Optimize images with Next.js Image component
- Use React.lazy for heavy components

### Runtime Performance
- Implement proper memoization with React.memo
- Use useMemo and useCallback judiciously
- Avoid unnecessary re-renders
- Profile with React DevTools

### Network Performance
- Implement efficient caching strategies
- Use React Query's background updates
- Implement proper loading states
- Minimize API calls with batching

## Troubleshooting

### Common Issues

1. **Import errors with path aliases**:
   - Check `tsconfig.json` paths configuration
   - Restart TypeScript server in VS Code

2. **Build errors**:
   - Clear cache: `npm run clean`
   - Delete `node_modules` and reinstall

3. **Test failures**:
   - Check mock implementations
   - Verify test environment setup

### Debugging

1. **Development debugging**:
   - Use React DevTools
   - Enable debug mode in environment variables
   - Use browser debugger with source maps

2. **Production debugging**:
   - Check browser console for errors
   - Verify environment variables
   - Check network tab for API failures

## Contributing

1. Follow the coding standards outlined above
2. Write comprehensive tests for new features
3. Update documentation for significant changes
4. Run all quality checks before submitting PRs
5. Follow the Git workflow outlined in the main repository

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev/)
- [Material-UI Documentation](https://mui.com/)
- [TanStack Query Documentation](https://tanstack.com/query)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

---

**Signature**: [architect_software-architecture-20250902]