/**
 * Application Constants and Configuration
 * Centralized constants for the Khive Dashboard application
 */

// API Configuration
export const API_CONFIG = {
  BASE_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:11634",
  TIMEOUT: 30000, // 30 seconds
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000, // Base delay in ms
} as const;

// Real-time Update Intervals
export const UPDATE_INTERVALS = {
  METRICS: 10000, // 10 seconds
  EVENTS: 2000, // 2 seconds
  FILE_LOCKS: 5000, // 5 seconds
  AGENTS: 5000, // 5 seconds
} as const;

// Query Stale Times (in milliseconds)
export const STALE_TIMES = {
  SHORT: 1000 * 60 * 2, // 2 minutes
  MEDIUM: 1000 * 60 * 5, // 5 minutes
  LONG: 1000 * 60 * 30, // 30 minutes
  VERY_LONG: 1000 * 60 * 60, // 1 hour
} as const;

// Agent Status Colors and States
export const AGENT_STATUS = {
  ACTIVE: "active",
  IDLE: "idle",
  ERROR: "error",
} as const;

export const AGENT_STATUS_COLORS = {
  [AGENT_STATUS.ACTIVE]: "#10b981", // Green
  [AGENT_STATUS.IDLE]: "#6b7280", // Gray
  [AGENT_STATUS.ERROR]: "#ef4444", // Red
} as const;

// Session Status
export const SESSION_STATUS = {
  PENDING: "pending",
  RUNNING: "running",
  COMPLETED: "completed",
  FAILED: "failed",
} as const;

export const SESSION_STATUS_COLORS = {
  [SESSION_STATUS.PENDING]: "#f59e0b", // Yellow
  [SESSION_STATUS.RUNNING]: "#3b82f6", // Blue
  [SESSION_STATUS.COMPLETED]: "#10b981", // Green
  [SESSION_STATUS.FAILED]: "#ef4444", // Red
} as const;

// Plan Node Status
export const PLAN_NODE_STATUS = {
  PENDING: "pending",
  RUNNING: "running",
  COMPLETED: "completed",
  FAILED: "failed",
} as const;

// Coordination Strategies
export const COORDINATION_STRATEGIES = {
  FAN_OUT_SYNTHESIZE: "FAN_OUT_SYNTHESIZE",
  PIPELINE: "PIPELINE",
  PARALLEL: "PARALLEL",
} as const;

// Event Types
export const EVENT_TYPES = {
  PRE_COMMAND: "pre_command",
  POST_COMMAND: "post_command",
  PRE_EDIT: "pre_edit",
  POST_EDIT: "post_edit",
  PRE_AGENT_SPAWN: "pre_agent_spawn",
  POST_AGENT_SPAWN: "post_agent_spawn",
} as const;

// Navigation Routes
export const ROUTES = {
  HOME: "/",
  DASHBOARD: "/dashboard",
  SESSIONS: "/dashboard/sessions",
  AGENTS: "/dashboard/agents",
  PLANS: "/dashboard/plans",
  METRICS: "/dashboard/metrics",
  EVENTS: "/dashboard/events",
  SETTINGS: "/dashboard/settings",
} as const;

// UI Configuration
export const UI_CONFIG = {
  SIDEBAR_WIDTH: 240,
  HEADER_HEIGHT: 64,
  DRAWER_WIDTH: 320,
  MAX_CONTENT_WIDTH: 1200,
  ANIMATION_DURATION: 300,
} as const;

// Chart Colors (for metrics and analytics)
export const CHART_COLORS = [
  "#3b82f6", // Blue
  "#10b981", // Green
  "#f59e0b", // Yellow
  "#ef4444", // Red
  "#8b5cf6", // Purple
  "#06b6d4", // Cyan
  "#f97316", // Orange
  "#84cc16", // Lime
  "#ec4899", // Pink
  "#6b7280", // Gray
] as const;

// File Extensions for Syntax Highlighting
export const FILE_EXTENSIONS = {
  PYTHON: [".py", ".pyx", ".pyi"],
  TYPESCRIPT: [".ts", ".tsx"],
  JAVASCRIPT: [".js", ".jsx"],
  JSON: [".json"],
  YAML: [".yml", ".yaml"],
  MARKDOWN: [".md", ".mdx"],
  TEXT: [".txt", ".log"],
} as const;

// Theme Mode Options
export const THEME_MODES = {
  LIGHT: "light",
  DARK: "dark",
  SYSTEM: "system",
} as const;

// Local Storage Keys
export const STORAGE_KEYS = {
  THEME_MODE: "theme-mode",
  SIDEBAR_COLLAPSED: "sidebar-collapsed",
  DASHBOARD_LAYOUT: "dashboard-layout",
  USER_PREFERENCES: "user-preferences",
} as const;

// Error Codes
export const ERROR_CODES = {
  NETWORK_ERROR: "NETWORK_ERROR",
  TIMEOUT: "TIMEOUT",
  UNAUTHORIZED: "UNAUTHORIZED",
  FORBIDDEN: "FORBIDDEN",
  NOT_FOUND: "NOT_FOUND",
  SERVER_ERROR: "SERVER_ERROR",
  VALIDATION_ERROR: "VALIDATION_ERROR",
} as const;
