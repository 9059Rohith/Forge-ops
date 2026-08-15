import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json({
    backendUrl: process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  });
}
