/**
 * Next.js API Route - Proxy for backend domains endpoint
 * Solves CORS issues by proxying to the khive daemon server
 */

import { NextResponse } from "next/server";

const BACKEND_URL = process.env.KHIVE_BACKEND_URL || "http://localhost:11634";

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/config/domains`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      console.error(
        `Backend domains API error: ${response.status} ${response.statusText}`,
      );
      return NextResponse.json(
        { error: "Failed to fetch domains from backend" },
        { status: response.status },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error proxying domains request to backend:", error);
    return NextResponse.json(
      { error: "Backend connection failed" },
      { status: 503 },
    );
  }
}
