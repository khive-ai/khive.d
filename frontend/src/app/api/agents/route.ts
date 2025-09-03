/**
 * Next.js API Route - Proxy for backend agent spawning endpoint
 * Solves CORS issues by proxying to the khive daemon server
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.KHIVE_BACKEND_URL || "http://localhost:11634";

export async function POST(request: NextRequest) {
  try {
    const requestBody = await request.json();

    const response = await fetch(`${BACKEND_URL}/api/agents`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      console.error(
        `Backend agents API error: ${response.status} ${response.statusText}`,
      );
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || "Failed to spawn agent" },
        { status: response.status },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error proxying agent spawn request to backend:", error);
    return NextResponse.json(
      { error: "Backend connection failed" },
      { status: 503 },
    );
  }
}

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/agents`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      console.error(
        `Backend agents list API error: ${response.status} ${response.statusText}`,
      );
      return NextResponse.json(
        { error: "Failed to fetch agents from backend" },
        { status: response.status },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error proxying agents list request to backend:", error);
    return NextResponse.json(
      { error: "Backend connection failed" },
      { status: 503 },
    );
  }
}
