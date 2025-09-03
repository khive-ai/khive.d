/**
 * Orchestration Section Layout
 * Provides consistent layout for orchestration-related pages
 */

import React from "react";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Orchestration Center | Khive AI",
  description:
    "Agent spawning, task management, and orchestration monitoring interface",
};

interface OrchestrationLayoutProps {
  children: React.ReactNode;
}

export default function OrchestrationLayout(
  { children }: OrchestrationLayoutProps,
) {
  return (
    <div className="orchestration-section">
      {children}
    </div>
  );
}
