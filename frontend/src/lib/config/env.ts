/**
 * Environment configuration for the Khive Dashboard
 * Validates and provides typed access to environment variables
 */

interface EnvironmentConfig {
  NODE_ENV: "development" | "production" | "test";

  // API Configuration
  API_BASE_URL: string;
  WEBSOCKET_URL: string;

  // Application Configuration
  APP_NAME: string;
  APP_VERSION: string;

  // Feature Flags
  ENABLE_DEBUG: boolean;
  ENABLE_ANALYTICS: boolean;
}

function getEnvironmentVariable(name: string, defaultValue?: string): string {
  const value = process.env[name] || process.env[`NEXT_PUBLIC_${name}`];

  if (!value && !defaultValue) {
    throw new Error(`Environment variable ${name} is required but not set`);
  }

  return value || defaultValue!;
}

function getBooleanEnvironmentVariable(
  name: string,
  defaultValue: boolean = false,
): boolean {
  const value = getEnvironmentVariable(name, defaultValue.toString());
  return value.toLowerCase() === "true";
}

export const env: EnvironmentConfig = {
  NODE_ENV: (process.env.NODE_ENV as EnvironmentConfig["NODE_ENV"]) ||
    "development",

  // API Configuration
  API_BASE_URL: getEnvironmentVariable(
    "API_BASE_URL",
    "http://localhost:3001/api",
  ),
  WEBSOCKET_URL: getEnvironmentVariable("WEBSOCKET_URL", "ws://localhost:3001"),

  // Application Configuration
  APP_NAME: getEnvironmentVariable("APP_NAME", "Khive Dashboard"),
  APP_VERSION: getEnvironmentVariable("APP_VERSION", "0.1.0"),

  // Feature Flags
  ENABLE_DEBUG: getBooleanEnvironmentVariable("ENABLE_DEBUG", true),
  ENABLE_ANALYTICS: getBooleanEnvironmentVariable("ENABLE_ANALYTICS", false),
};

// Validate environment on startup
if (typeof window === "undefined") {
  console.log("🔧 Environment Configuration Loaded:", {
    NODE_ENV: env.NODE_ENV,
    API_BASE_URL: env.API_BASE_URL,
    WEBSOCKET_URL: env.WEBSOCKET_URL,
    APP_NAME: env.APP_NAME,
  });
}

export default env;
