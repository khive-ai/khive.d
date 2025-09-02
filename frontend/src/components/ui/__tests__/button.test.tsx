/**
 * Button Component Tests
 * Unit tests for the Button UI component
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import { createTheme } from '@mui/material/styles';
import { Button } from '../button';

const theme = createTheme();

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

describe('Button', () => {
  it('renders correctly', () => {
    renderWithTheme(<Button>Test Button</Button>);
    expect(screen.getByRole('button', { name: 'Test Button' })).toBeInTheDocument();
  });

  it('handles click events', () => {
    const handleClick = jest.fn();
    renderWithTheme(<Button onClick={handleClick}>Click me</Button>);
    
    fireEvent.click(screen.getByRole('button', { name: 'Click me' }));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('shows loading state correctly', () => {
    renderWithTheme(
      <Button loading>
        Loading Button
      </Button>
    );
    
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('applies variant styles correctly', () => {
    renderWithTheme(
      <Button variant="destructive">
        Delete
      </Button>
    );
    
    const button = screen.getByRole('button');
    expect(button).toHaveClass('MuiButton-root');
  });

  it('applies size variants correctly', () => {
    renderWithTheme(
      <Button size="sm">
        Small Button
      </Button>
    );
    
    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
  });

  it('is disabled when disabled prop is true', () => {
    renderWithTheme(
      <Button disabled>
        Disabled Button
      </Button>
    );
    
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('forwards ref correctly', () => {
    const ref = { current: null };
    renderWithTheme(
      <Button ref={ref as any}>
        Ref Button
      </Button>
    );
    
    expect(ref.current).toBeInstanceOf(HTMLButtonElement);
  });

  it('applies custom className', () => {
    renderWithTheme(
      <Button className="custom-class">
        Custom Button
      </Button>
    );
    
    const button = screen.getByRole('button');
    expect(button).toHaveClass('custom-class');
  });

  it('prevents click when loading', () => {
    const handleClick = jest.fn();
    renderWithTheme(
      <Button loading onClick={handleClick}>
        Loading Button
      </Button>
    );
    
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('displays children correctly', () => {
    renderWithTheme(
      <Button>
        <span>Icon</span>
        Button Text
      </Button>
    );
    
    expect(screen.getByText('Icon')).toBeInTheDocument();
    expect(screen.getByText('Button Text')).toBeInTheDocument();
  });
});