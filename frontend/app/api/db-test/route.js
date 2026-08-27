import { NextResponse } from "next/server";
import connectDb from "@/lib/mongodb";

export async function GET() {
  try {
    await connectDb();

    return NextResponse.json({
      success: true,
      message: "MongoDB connected successfully",
      database: "labelcheck",
    });
  } catch (error) {
    console.error("MongoDB connection failed:", error);

    return NextResponse.json(
      {
        success: false,
        message: "MongoDB connection failed",
      },
      { status: 500 }
    );
  }
}