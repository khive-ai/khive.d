/**
 * Live Coordination Monitor Page
 * Dedicated page for real-time agent coordination monitoring
 */

"use client";

import React from "react";
import { useSearchParams } from "next/navigation";
import { LiveCoordinationMonitor } from "@/components/feature/live-coordination-monitor";

export default function LiveMonitorPage() {
  const searchParams = useSearchParams();
  const coordinationId = searchParams.get("coordination_id") || undefined;

  return (
    <LiveCoordinationMonitor
      coordinationId={coordinationId}
      maxActivityEvents={100}
      autoRefresh={true}
      refreshInterval={2000}
    />
  );
}
