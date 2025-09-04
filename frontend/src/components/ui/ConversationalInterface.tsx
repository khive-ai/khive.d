"use client";

import { useState, useCallback, useEffect, useRef } from 'react';
import {
  Dialog,
  Box,
  InputBase,
  Typography,
  Button,
  IconButton,
  Paper,
  Chip,
  Fade,
  CircularProgress,
  useTheme
} from '@mui/material';
import {
  Send as SendIcon,
  Close as CloseIcon,
  Lightbulb as LightbulbIcon,
  AutoAwesome as AIIcon,
  History as HistoryIcon
} from '@mui/icons-material';

interface IntentSuggestion {
  id: string;
  userFriendlyText: string;
  description: string;
  confidence: number;
  category: 'create' | 'analyze' | 'monitor' | 'manage' | 'help';
}

interface ConversationMessage {
  id: string;
  type: 'user' | 'ai' | 'system';
  content: string;
  timestamp: Date;
  suggestions?: IntentSuggestion[];
}

interface ConversationalInterfaceProps {
  open: boolean;
  onClose: () => void;
  onExecuteIntent: (intent: string, originalText: string) => void;
  onNavigate?: (view: 'planning' | 'monitoring' | 'analytics' | 'agents' | 'settings') => void;
}

const EXAMPLE_PROMPTS = [
  "Analyze the performance of my current project",
  "Create a new workflow to process customer data", 
  "Set up monitoring for system health",
  "Help me understand what's happening in my project",
  "Optimize the current task execution"
];

const RECENT_CONVERSATIONS = [
  "Analyzed project performance metrics",
  "Created data processing workflow", 
  "Set up system monitoring",
  "Optimized task execution flow"
];

/**
 * Revolutionary Conversational Interface
 * 
 * Transforms KHIVE from CLI-first to natural language interaction.
 * Users describe what they want to accomplish in plain English,
 * AI interprets intent and orchestrates the appropriate actions.
 * 
 * Key Features:
 * - Natural language input processing
 * - Intent recognition and suggestion
 * - Progressive disclosure for power users
 * - Conversational flow with context
 * - User-friendly language throughout
 */
export function ConversationalInterface({ 
  open, 
  onClose, 
  onExecuteIntent, 
  onNavigate 
}: ConversationalInterfaceProps) {
  const theme = useTheme();
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);
  const [suggestions, setSuggestions] = useState<IntentSuggestion[]>([]);
  const [showExamples, setShowExamples] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);

  // Welcome message when dialog opens
  useEffect(() => {
    if (open && conversation.length === 0) {
      setConversation([{
        id: 'welcome',
        type: 'ai',
        content: "Hi! I'm your AI assistant. Tell me what you'd like to accomplish with your project, and I'll help orchestrate the right actions.",
        timestamp: new Date()
      }]);
      setShowExamples(true);
    }
  }, [open, conversation.length]);

  // Focus input when dialog opens
  useEffect(() => {
    if (open && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [open]);

  // Natural Language Intent Processing
  const processNaturalLanguageInput = useCallback((userInput: string): IntentSuggestion[] => {
    const input_lower = userInput.toLowerCase();
    const suggestions: IntentSuggestion[] = [];

    // Analyze intent patterns and map to user-friendly actions
    if (input_lower.includes('analyze') || input_lower.includes('performance') || input_lower.includes('metrics')) {
      suggestions.push({
        id: 'analyze_project',
        userFriendlyText: 'Analyze project performance and metrics',
        description: 'Get insights into your project\'s performance, resource usage, and optimization opportunities',
        confidence: 0.9,
        category: 'analyze'
      });
    }

    if (input_lower.includes('create') || input_lower.includes('new') || input_lower.includes('build') || input_lower.includes('setup')) {
      suggestions.push({
        id: 'create_workflow',
        userFriendlyText: 'Create a new workflow',
        description: 'Design and set up a new automated workflow tailored to your requirements',
        confidence: 0.8,
        category: 'create'
      });
    }

    if (input_lower.includes('monitor') || input_lower.includes('track') || input_lower.includes('watch') || input_lower.includes('status')) {
      suggestions.push({
        id: 'setup_monitoring',
        userFriendlyText: 'Set up monitoring and alerts',
        description: 'Configure real-time monitoring for your systems and processes',
        confidence: 0.85,
        category: 'monitor'
      });
    }

    if (input_lower.includes('optimize') || input_lower.includes('improve') || input_lower.includes('faster') || input_lower.includes('better')) {
      suggestions.push({
        id: 'optimize_system',
        userFriendlyText: 'Optimize system performance',
        description: 'Identify and implement performance improvements across your workflows',
        confidence: 0.8,
        category: 'manage'
      });
    }

    if (input_lower.includes('help') || input_lower.includes('understand') || input_lower.includes('explain') || input_lower.includes('learn')) {
      suggestions.push({
        id: 'get_help',
        userFriendlyText: 'Get guidance and explanations',
        description: 'Learn about your system and get personalized recommendations',
        confidence: 0.9,
        category: 'help'
      });
    }

    if (input_lower.includes('manage') || input_lower.includes('organize') || input_lower.includes('control')) {
      suggestions.push({
        id: 'manage_resources',
        userFriendlyText: 'Manage resources and configurations',
        description: 'Organize and control your project resources, agents, and settings',
        confidence: 0.75,
        category: 'manage'
      });
    }

    // If no specific intent detected, offer general assistance
    if (suggestions.length === 0) {
      suggestions.push({
        id: 'general_assistance',
        userFriendlyText: 'Get personalized assistance',
        description: 'Let me help you accomplish what you have in mind with a custom approach',
        confidence: 0.6,
        category: 'help'
      });
    }

    return suggestions.sort((a, b) => b.confidence - a.confidence);
  }, []);

  // Handle user input submission
  const handleSubmit = useCallback(async () => {
    if (!input.trim() || isProcessing) return;

    const userMessage: ConversationMessage = {
      id: `user_${Date.now()}`,
      type: 'user',
      content: input.trim(),
      timestamp: new Date()
    };

    // Add user message to conversation
    setConversation(prev => [...prev, userMessage]);
    setShowExamples(false);
    setIsProcessing(true);

    // Process natural language to generate suggestions
    const intentSuggestions = processNaturalLanguageInput(input);
    setSuggestions(intentSuggestions);

    // Add AI response with suggestions
    const aiResponse: ConversationMessage = {
      id: `ai_${Date.now()}`,
      type: 'ai',
      content: intentSuggestions.length > 0 
        ? "I understand what you're looking for! Here are some ways I can help:" 
        : "Let me help you with that. I'll create a custom solution for your request.",
      timestamp: new Date(),
      suggestions: intentSuggestions
    };

    setTimeout(() => {
      setConversation(prev => [...prev, aiResponse]);
      setIsProcessing(false);
    }, 800); // Simulate AI processing time

    setInput('');
  }, [input, isProcessing, processNaturalLanguageInput]);

  // Handle suggestion selection
  const handleSuggestionSelect = useCallback((suggestion: IntentSuggestion) => {
    // Add system message showing selection
    const systemMessage: ConversationMessage = {
      id: `system_${Date.now()}`,
      type: 'system',
      content: `Executing: ${suggestion.userFriendlyText}`,
      timestamp: new Date()
    };

    setConversation(prev => [...prev, systemMessage]);
    
    // Execute the intent
    onExecuteIntent(suggestion.id, suggestion.userFriendlyText);
    
    // Close dialog after execution
    setTimeout(() => {
      onClose();
    }, 1000);
  }, [onExecuteIntent, onClose]);

  // Handle example prompt selection
  const handleExampleSelect = useCallback((example: string) => {
    setInput(example);
    setShowExamples(false);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  const getCategoryIcon = (category: IntentSuggestion['category']) => {
    switch (category) {
      case 'create': return '🚀';
      case 'analyze': return '📊';
      case 'monitor': return '👀';
      case 'manage': return '⚙️';
      case 'help': return '💡';
      default: return '✨';
    }
  };

  const getCategoryColor = (category: IntentSuggestion['category']) => {
    switch (category) {
      case 'create': return theme.palette.success.main;
      case 'analyze': return theme.palette.info.main;
      case 'monitor': return theme.palette.warning.main;
      case 'manage': return theme.palette.secondary.main;
      case 'help': return theme.palette.primary.main;
      default: return theme.palette.text.secondary;
    }
  };

  return (
    <Dialog
      data-testid="conversational-interface"
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          bgcolor: 'background.paper',
          borderRadius: 3,
          minHeight: '60vh',
          maxHeight: '80vh'
        }
      }}
    >
      {/* Header */}
      <Box sx={{ 
        p: 3, 
        pb: 2,
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        borderBottom: `1px solid ${theme.palette.divider}`
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <AIIcon sx={{ color: theme.palette.primary.main, fontSize: 28 }} />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            AI Assistant
          </Typography>
        </Box>
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </Box>

      {/* Conversation Area */}
      <Box sx={{ 
        flex: 1, 
        p: 3, 
        maxHeight: '400px', 
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: 2
      }}>
        {/* Conversation Messages */}
        {conversation.map((message) => (
          <Box key={message.id}>
            <Box sx={{ 
              display: 'flex', 
              justifyContent: message.type === 'user' ? 'flex-end' : 'flex-start',
              mb: 1
            }}>
              <Paper sx={{ 
                p: 2, 
                maxWidth: '70%',
                bgcolor: message.type === 'user' 
                  ? theme.palette.primary.main 
                  : message.type === 'system'
                  ? theme.palette.success.main
                  : theme.palette.grey[100],
                color: message.type === 'user' || message.type === 'system' ? 'white' : 'inherit',
                borderRadius: 2
              }}>
                <Typography variant="body1">
                  {message.content}
                </Typography>
              </Paper>
            </Box>

            {/* Suggestions */}
            {message.suggestions && message.suggestions.length > 0 && (
              <Box sx={{ ml: 2, mt: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                {message.suggestions.map((suggestion) => (
                  <Button
                    key={suggestion.id}
                    variant="outlined"
                    onClick={() => handleSuggestionSelect(suggestion)}
                    sx={{
                      justifyContent: 'flex-start',
                      textAlign: 'left',
                      borderColor: getCategoryColor(suggestion.category),
                      '&:hover': {
                        bgcolor: `${getCategoryColor(suggestion.category)}10`,
                        borderColor: getCategoryColor(suggestion.category)
                      }
                    }}
                    startIcon={<span>{getCategoryIcon(suggestion.category)}</span>}
                  >
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        {suggestion.userFriendlyText}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {suggestion.description}
                      </Typography>
                    </Box>
                  </Button>
                ))}
              </Box>
            )}
          </Box>
        ))}

        {/* Processing Indicator */}
        {isProcessing && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, ml: 2 }}>
            <CircularProgress size={16} />
            <Typography variant="body2" color="text.secondary">
              AI is thinking...
            </Typography>
          </Box>
        )}

        {/* Welcome Examples */}
        {showExamples && (
          <Fade in={showExamples}>
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <LightbulbIcon fontSize="small" />
                Try asking something like:
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {EXAMPLE_PROMPTS.map((prompt, index) => (
                  <Chip
                    key={index}
                    label={prompt}
                    variant="outlined"
                    clickable
                    onClick={() => handleExampleSelect(prompt)}
                    sx={{ 
                      justifyContent: 'flex-start',
                      height: 'auto',
                      py: 1,
                      '& .MuiChip-label': {
                        whiteSpace: 'normal',
                        textAlign: 'left'
                      }
                    }}
                  />
                ))}
              </Box>

              {RECENT_CONVERSATIONS.length > 0 && (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                    <HistoryIcon fontSize="small" />
                    Recent conversations:
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {RECENT_CONVERSATIONS.map((conversation, index) => (
                      <Chip
                        key={index}
                        label={conversation}
                        size="small"
                        clickable
                        onClick={() => handleExampleSelect(`Tell me more about: ${conversation}`)}
                      />
                    ))}
                  </Box>
                </Box>
              )}
            </Box>
          </Fade>
        )}
      </Box>

      {/* Input Area */}
      <Box sx={{ 
        p: 3, 
        pt: 2,
        borderTop: `1px solid ${theme.palette.divider}`,
        bgcolor: theme.palette.grey[50]
      }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-end' }}>
          <InputBase
            ref={inputRef}
            data-testid="conversation-input"
            placeholder="Describe what you'd like to accomplish..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            multiline
            maxRows={3}
            sx={{
              flex: 1,
              p: 2,
              bgcolor: 'white',
              borderRadius: 2,
              border: `1px solid ${theme.palette.divider}`,
              fontSize: '16px',
              '&:focus-within': {
                borderColor: theme.palette.primary.main,
                boxShadow: `0 0 0 2px ${theme.palette.primary.main}20`
              }
            }}
          />
          <Button
            data-testid="send-button"
            variant="contained"
            onClick={handleSubmit}
            disabled={!input.trim() || isProcessing}
            sx={{ 
              minWidth: 48,
              height: 48,
              borderRadius: 2
            }}
          >
            <SendIcon />
          </Button>
        </Box>
        
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          💡 Describe your goal in natural language - I'll figure out the best way to help
        </Typography>
      </Box>
    </Dialog>
  );
}