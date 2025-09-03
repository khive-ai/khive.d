/**
 * Agent Composition Page - Next.js App Router Integration
 * Architectural Pattern: Page-level Container with Component Composition
 */

"use client";

import React from "react";
import { Box, Container } from "@mui/material";
import { AgentComposer } from "@/components/agent-composer";
import type { AgentComposition } from "@/components/agent-composer";

/**
 * Agent Composition Page
 *
 * Provides interface for composing intelligent agents by combining roles with domain expertise.
 * Uses the Agent Composer Studio component set to guide users through:
 * 1. Role and domain selection
 * 2. Capability preview and validation
 * 3. Basic testing interface
 * 4. Final composition and deployment
 */
export default function ComposePage() {
  // Handle completed agent composition
  const handleAgentComposed = (composition: AgentComposition) => {
    console.log("Agent composition completed:", composition);

    // In a production implementation, this would:
    // 1. Save the composition to the backend
    // 2. Deploy the agent to the orchestration system
    // 3. Navigate to the agent management page
    // 4. Show success notification

    // For MVP, we'll just log and could show a success message
    alert(
      `Agent "${composition.role?.name} + ${composition.domain?.name}" has been successfully composed!`,
    );
  };

  return (
    <Container maxWidth={false} disableGutters>
      <Box
        sx={{
          minHeight: "100vh",
          bgcolor: "background.default",
          py: 2,
        }}
      >
        <AgentComposer onAgentComposed={handleAgentComposed} />
      </Box>
    </Container>
  );
}
