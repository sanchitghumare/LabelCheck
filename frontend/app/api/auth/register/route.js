import { NextResponse } from "next/server";
import bcrypt from "bcryptjs";

import connectDb from "@/lib/mongodb";
import User from "@/models/User";

export async function POST(request) {
  try {
    const body = await request.json();

    const { name, email, password } = body;

    // -----------------------------
    // Validate input
    // -----------------------------

    if (
      typeof name !== "string" ||
      typeof email !== "string" ||
      typeof password !== "string"
    ) {
      return NextResponse.json(
        {
          success: false,
          message: "Name, email and password are required.",
        },
        { status: 400 }
      );
    }

    const cleanName = name.trim();
    const cleanEmail = email.toLowerCase().trim();

    if (!cleanName) {
      return NextResponse.json(
        {
          success: false,
          message: "Name cannot be empty.",
        },
        { status: 400 }
      );
    }

    if (cleanName.length > 100) {
      return NextResponse.json(
        {
          success: false,
          message: "Name must be 100 characters or less.",
        },
        { status: 400 }
      );
    }

    if (!cleanEmail) {
      return NextResponse.json(
        {
          success: false,
          message: "Email cannot be empty.",
        },
        { status: 400 }
      );
    }

    if (password.length < 8) {
      return NextResponse.json(
        {
          success: false,
          message: "Password must be at least 8 characters long.",
        },
        { status: 400 }
      );
    }

    // -----------------------------
    // Connect to MongoDB
    // -----------------------------

    await connectDb();

    // -----------------------------
    // Check duplicate email
    // -----------------------------

    const existingUser = await User.findOne({
      email: cleanEmail,
    }).lean();

    if (existingUser) {
      return NextResponse.json(
        {
          success: false,
          message: "An account with this email already exists.",
        },
        { status: 409 }
      );
    }

    // -----------------------------
    // Hash password
    // -----------------------------

    const passwordHash = await bcrypt.hash(password, 12);

    // -----------------------------
    // Create user
    // -----------------------------

    const user = await User.create({
      name: cleanName,
      email: cleanEmail,
      passwordHash,
      role: "user",
    });

    return NextResponse.json(
      {
        success: true,
        message: "Account created successfully.",
        user: {
          id: user._id.toString(),
          name: user.name,
          email: user.email,
          role: user.role,
        },
      },
      { status: 201 }
    );
  } catch (error) {
    console.error("Registration failed:", error);

    // Handle MongoDB unique-index race condition.
    if (error?.code === 11000) {
      return NextResponse.json(
        {
          success: false,
          message: "An account with this email already exists.",
        },
        { status: 409 }
      );
    }

    return NextResponse.json(
      {
        success: false,
        message: "Unable to create account.",
      },
      { status: 500 }
    );
  }
}