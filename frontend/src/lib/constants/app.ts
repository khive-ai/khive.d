/**
 * Application constants for the Khive Dashboard
 */

// Route Constants
export const ROUTES = {
  HOME: "/",
  DASHBOARD: "/dashboard",
  AGENTS: "/dashboard/agents",
  SESSIONS: "/dashboard/sessions",
  COORDINATION: "/dashboard/coordination",
  PLANS: "/dashboard/plans",
  SETTINGS: "/dashboard/settings",
} as const;

// Agent Status Constants
export const AGENT_STATUS = {
  ACTIVE: "active",
  IDLE: "idle",
  ERROR: "error",
} as const;

// Session Status Constants
export const SESSION_STATUS = {
  RUNNING: "running",
  FAILED: "failed",
  COMPLETED: "completed",
  PENDING: "pending",
} as const;

// Coordination Strategy Constants
export const COORDINATION_STRATEGY = {
  FAN_OUT_SYNTHESIZE: "FAN_OUT_SYNTHESIZE",
  PIPELINE: "PIPELINE",
  PARALLEL: "PARALLEL",
} as const;

// Event Type Constants
export const EVENT_TYPES = {
  PRE_COMMAND: "pre_command",
  POST_COMMAND: "post_command",
  PRE_EDIT: "pre_edit",
  POST_EDIT: "post_edit",
  PRE_AGENT_SPAWN: "pre_agent_spawn",
  POST_AGENT_SPAWN: "post_agent_spawn",
} as const;

// Plan Node Status Constants
export const PLAN_NODE_STATUS = {
  PENDING: "pending",
  RUNNING: "running",
  COMPLETED: "completed",
  FAILED: "failed",
} as const;

// UI Constants
export const UI_CONSTANTS = {
  DEBOUNCE_DELAY: 300,
  ANIMATION_DURATION: 200,
  POLLING_INTERVAL: 5000,
  WEBSOCKET_RECONNECT_DELAY: 3000,
  DEFAULT_PAGE_SIZE: 25,
  MAX_RETRY_ATTEMPTS: 3,
} as const;

// Theme Constants
export const THEME = {
  BREAKPOINTS: {
    XS: 0,
    SM: 600,
    MD: 960,
    LG: 1280,
    XL: 1920,
  },
  SPACING: {
    XS: 4,
    SM: 8,
    MD: 16,
    LG: 24,
    XL: 32,
  },
  COLORS: {
    PRIMARY: "#1976d2",
    SECONDARY: "#dc004e",
    SUCCESS: "#2e7d32",
    WARNING: "#ed6c02",
    ERROR: "#d32f2f",
    INFO: "#0288d1",
  },
} as const;

// Validation Constants
export const VALIDATION = {
  MIN_PASSWORD_LENGTH: 8,
  MAX_TEXT_LENGTH: 1000,
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  ALLOWED_FILE_TYPES: [
    "image/jpeg",
    "image/png",
    "image/gif",
    "application/pdf",
  ],
} as const;

// API Constants
export const API = {
  TIMEOUT: 30000, // 30 seconds
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000,
} as const;

// Local Storage Keys
export const STORAGE_KEYS = {
  AUTH_TOKEN: "khive_auth_token",
  USER_PREFERENCES: "khive_user_preferences",
  DASHBOARD_LAYOUT: "khive_dashboard_layout",
  THEME_MODE: "khive_theme_mode",
} as const;

export type RouteType = (typeof ROUTES)[keyof typeof ROUTES];
export type AgentStatusType = (typeof AGENT_STATUS)[keyof typeof AGENT_STATUS];
export type SessionStatusType =
  (typeof SESSION_STATUS)[keyof typeof SESSION_STATUS];
export type CoordinationStrategyType =
  (typeof COORDINATION_STRATEGY)[keyof typeof COORDINATION_STRATEGY];
export type EventTypeType = (typeof EVENT_TYPES)[keyof typeof EVENT_TYPES];
export type PlanNodeStatusType =
  (typeof PLAN_NODE_STATUS)[keyof typeof PLAN_NODE_STATUS];
