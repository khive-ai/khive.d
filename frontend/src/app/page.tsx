"use client";

import React from 'react';
import { ProfessionalWorkspace } from '@/components/workspace/ProfessionalWorkspace';

/**
 * KHIVE Professional Orchestration Workspace
 * 
 * Clean 3-panel interface for AI orchestration and project management.
 * Professional design with direct access to KHIVE functionality.
 * 
 * Key Features:
 * - Session/project management
 * - Direct action controls
 * - Orchestration visualization
 * - Professional workflow design
 * - No modal interruptions
 */
export default function HomePage() {
  return (
    <>
      {/* Professional KHIVE Workspace */}
      <ProfessionalWorkspace />
      
      {/* Hidden test elements for E2E framework validation */}
      <div 
        className="hidden" 
        data-testid="test-markers"
        data-test-environment="playwright"
        data-khive-test-mode="true"
      >
        Test markers for E2E validation - Updated for professional interface
      </div>
    </>
  );
}