/**
 * Theme Provider for Material-UI with dark/light mode support
 * Integrates with async state management patterns
 */

"use client";

import { createTheme, ThemeProvider } from "@mui/material/styles";
import { CssBaseline } from "@mui/material";
import {
  createContext,
  ReactNode,
  useContext,
  useEffect,
  useState,
} from "react";

type ThemeMode = "light" | "dark" | "system";

interface ThemeContextValue {
  mode: ThemeMode;
  actualMode: "light" | "dark";
  setMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a CustomThemeProvider");
  }
  return context;
}

interface Props {
  children: ReactNode;
}

export function CustomThemeProvider({ children }: Props) {
  const [mode, setMode] = useState<ThemeMode>("system");
  const [actualMode, setActualMode] = useState<"light" | "dark">("light");

  // Determine actual theme mode based on user preference and system preference
  useEffect(() => {
    const savedMode = localStorage.getItem("theme-mode") as ThemeMode;
    if (savedMode && ["light", "dark", "system"].includes(savedMode)) {
      setMode(savedMode);
    }
  }, []);

  useEffect(() => {
    const determineActualMode = () => {
      if (mode === "system") {
        return window.matchMedia("(prefers-color-scheme: dark)").matches
          ? "dark"
          : "light";
      }
      return mode;
    };

    const updateActualMode = () => {
      setActualMode(determineActualMode());
    };

    updateActualMode();

    if (mode === "system") {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      mediaQuery.addEventListener("change", updateActualMode);
      return () => mediaQuery.removeEventListener("change", updateActualMode);
    }
  }, [mode]);

  const handleSetMode = (newMode: ThemeMode) => {
    setMode(newMode);
    localStorage.setItem("theme-mode", newMode);
  };

  // Create Material-UI theme
  const theme = createTheme({
    palette: {
      mode: actualMode,
      primary: {
        main: actualMode === "dark" ? "#60a5fa" : "#2563eb",
        dark: actualMode === "dark" ? "#3b82f6" : "#1d4ed8",
        light: actualMode === "dark" ? "#93c5fd" : "#60a5fa",
      },
      secondary: {
        main: actualMode === "dark" ? "#a78bfa" : "#7c3aed",
        dark: actualMode === "dark" ? "#8b5cf6" : "#5b21b6",
        light: actualMode === "dark" ? "#c4b5fd" : "#a78bfa",
      },
      background: {
        default: actualMode === "dark" ? "#0f172a" : "#f8fafc",
        paper: actualMode === "dark" ? "#1e293b" : "#ffffff",
      },
      text: {
        primary: actualMode === "dark" ? "#f1f5f9" : "#0f172a",
        secondary: actualMode === "dark" ? "#cbd5e1" : "#475569",
      },
      divider: actualMode === "dark" ? "#334155" : "#e2e8f0",
      error: {
        main: "#ef4444",
        dark: "#dc2626",
        light: "#f87171",
      },
      warning: {
        main: "#f59e0b",
        dark: "#d97706",
        light: "#fbbf24",
      },
      success: {
        main: "#10b981",
        dark: "#059669",
        light: "#34d399",
      },
      info: {
        main: "#3b82f6",
        dark: "#2563eb",
        light: "#60a5fa",
      },
    },
    typography: {
      fontFamily: [
        "-apple-system",
        "BlinkMacSystemFont",
        '"Segoe UI"',
        "Roboto",
        '"Helvetica Neue"',
        "Arial",
        "sans-serif",
        '"Apple Color Emoji"',
        '"Segoe UI Emoji"',
        '"Segoe UI Symbol"',
      ].join(","),
      h1: {
        fontWeight: 700,
        fontSize: "2.5rem",
        lineHeight: 1.2,
      },
      h2: {
        fontWeight: 600,
        fontSize: "2rem",
        lineHeight: 1.3,
      },
      h3: {
        fontWeight: 600,
        fontSize: "1.5rem",
        lineHeight: 1.4,
      },
      h4: {
        fontWeight: 600,
        fontSize: "1.25rem",
        lineHeight: 1.4,
      },
      body1: {
        fontSize: "1rem",
        lineHeight: 1.6,
      },
      body2: {
        fontSize: "0.875rem",
        lineHeight: 1.5,
      },
    },
    shape: {
      borderRadius: 8,
    },
    components: {
      MuiButton: {
        styleOverrides: {
          root: {
            textTransform: "none",
            fontWeight: 500,
            borderRadius: 6,
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: 12,
            boxShadow: actualMode === "dark"
              ? "0 1px 3px 0 rgba(0, 0, 0, 0.3), 0 1px 2px 0 rgba(0, 0, 0, 0.2)"
              : "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)",
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
          },
        },
      },
    },
  });

  const contextValue: ThemeContextValue = {
    mode,
    actualMode,
    setMode: handleSetMode,
  };

  return (
    <ThemeContext.Provider value={contextValue}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ThemeContext.Provider>
  );
}

export default CustomThemeProvider;
