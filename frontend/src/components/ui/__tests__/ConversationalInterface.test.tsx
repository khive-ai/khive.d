import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { ConversationalInterface } from '../ConversationalInterface';

// Mock theme for testing
const theme = createTheme();

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>{children}</ThemeProvider>
);

describe('ConversationalInterface', () => {
  const mockOnClose = jest.fn();
  const mockOnExecuteIntent = jest.fn();
  const mockOnNavigate = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  const renderComponent = (props = {}) => {
    const defaultProps = {
      open: true,
      onClose: mockOnClose,
      onExecuteIntent: mockOnExecuteIntent,
      onNavigate: mockOnNavigate,
      ...props,
    };

    return render(
      <TestWrapper>
        <ConversationalInterface {...defaultProps} />
      </TestWrapper>
    );
  };

  it('renders conversational interface when open', () => {
    renderComponent();
    
    expect(screen.getByTestId('conversational-interface')).toBeInTheDocument();
    expect(screen.getByText('AI Assistant')).toBeInTheDocument();
    expect(screen.getByTestId('conversation-input')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    renderComponent({ open: false });
    
    expect(screen.queryByTestId('conversational-interface')).not.toBeInTheDocument();
  });

  it('shows welcome message when opened', () => {
    renderComponent();
    
    expect(screen.getByText(/Hi! I'm your AI assistant/)).toBeInTheDocument();
    expect(screen.getByText(/Try asking something like:/)).toBeInTheDocument();
  });

  it('displays example prompts', () => {
    renderComponent();
    
    expect(screen.getByText('Analyze the performance of my current project')).toBeInTheDocument();
    expect(screen.getByText('Create a new workflow to process customer data')).toBeInTheDocument();
  });

  it('allows user to type in input field', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    const input = screen.getByTestId('conversation-input');
    await user.type(input, 'Help me analyze my project performance');
    
    expect(input).toHaveValue('Help me analyze my project performance');
  });

  it('processes user input and shows AI response', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    const input = screen.getByTestId('conversation-input');
    const sendButton = screen.getByTestId('send-button');
    
    await user.type(input, 'analyze my project performance');
    await user.click(sendButton);
    
    await waitFor(() => {
      expect(screen.getByText('analyze my project performance')).toBeInTheDocument();
      expect(screen.getByText(/I understand what you're looking for/)).toBeInTheDocument();
    });
  });

  it('shows intent suggestions based on user input', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    const input = screen.getByTestId('conversation-input');
    const sendButton = screen.getByTestId('send-button');
    
    await user.type(input, 'analyze performance metrics');
    await user.click(sendButton);
    
    await waitFor(() => {
      expect(screen.getByText('Analyze project performance and metrics')).toBeInTheDocument();
    });
  });

  it('executes intent when suggestion is clicked', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    const input = screen.getByTestId('conversation-input');
    const sendButton = screen.getByTestId('send-button');
    
    await user.type(input, 'analyze my project');
    await user.click(sendButton);
    
    await waitFor(() => {
      const suggestion = screen.getByText('Analyze project performance and metrics');
      expect(suggestion).toBeInTheDocument();
    });
    
    const suggestionButton = screen.getByText('Analyze project performance and metrics').closest('button');
    if (suggestionButton) {
      await user.click(suggestionButton);
    }
    
    expect(mockOnExecuteIntent).toHaveBeenCalledWith(
      'analyze_project',
      'Analyze project performance and metrics'
    );
  });

  it('closes when close button is clicked', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    const closeButton = screen.getByRole('button', { name: /close/i });
    await user.click(closeButton);
    
    expect(mockOnClose).toHaveBeenCalled();
  });

  it('allows selecting example prompts', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    const examplePrompt = screen.getByText('Analyze the performance of my current project');
    await user.click(examplePrompt);
    
    const input = screen.getByTestId('conversation-input');
    expect(input).toHaveValue('Analyze the performance of my current project');
  });

  it('handles Enter key submission', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    const input = screen.getByTestId('conversation-input');
    await user.type(input, 'help me create a workflow');
    await user.keyboard('{Enter}');
    
    await waitFor(() => {
      expect(screen.getByText('help me create a workflow')).toBeInTheDocument();
    });
  });

  it('disables send button when input is empty', () => {
    renderComponent();
    
    const sendButton = screen.getByTestId('send-button');
    expect(sendButton).toBeDisabled();
  });

  it('enables send button when input has text', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    const input = screen.getByTestId('conversation-input');
    const sendButton = screen.getByTestId('send-button');
    
    await user.type(input, 'test input');
    
    expect(sendButton).not.toBeDisabled();
  });

  it('shows processing indicator during AI response', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    const input = screen.getByTestId('conversation-input');
    const sendButton = screen.getByTestId('send-button');
    
    await user.type(input, 'test message');
    await user.click(sendButton);
    
    // Should show processing state briefly
    expect(screen.getByText('AI is thinking...')).toBeInTheDocument();
    
    // Wait for processing to complete
    await waitFor(() => {
      expect(screen.queryByText('AI is thinking...')).not.toBeInTheDocument();
    });
  });

  it('categorizes intents correctly', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    const input = screen.getByTestId('conversation-input');
    const sendButton = screen.getByTestId('send-button');
    
    await user.type(input, 'create a new workflow');
    await user.click(sendButton);
    
    await waitFor(() => {
      expect(screen.getByText('🚀')).toBeInTheDocument(); // Create category icon
    });
  });

  it('handles multiple conversation turns', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    const input = screen.getByTestId('conversation-input');
    const sendButton = screen.getByTestId('send-button');
    
    // First message
    await user.type(input, 'analyze performance');
    await user.click(sendButton);
    
    await waitFor(() => {
      expect(screen.getByText('analyze performance')).toBeInTheDocument();
    });
    
    // Second message
    await user.type(input, 'create workflow');
    await user.click(sendButton);
    
    await waitFor(() => {
      expect(screen.getByText('create workflow')).toBeInTheDocument();
    });
    
    // Both messages should be visible
    expect(screen.getByText('analyze performance')).toBeInTheDocument();
    expect(screen.getByText('create workflow')).toBeInTheDocument();
  });
});