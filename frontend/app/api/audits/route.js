import { getServerSession } from "next-auth";

import { authOptions } from "@/auth";
import connectDb from "@/lib/mongodb";
import Audit from "@/models/Audit";

export async function GET() {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.id) {
      return Response.json(
        {
          success: false,
          message: "Authentication required.",
        },
        { status: 401 }
      );
    }

    await connectDb();

    const audits = await Audit.find({
      userId: session.user.id,
    })
      .sort({ timestamp: -1 })
      .lean();

    return Response.json({
      success: true,
      audits,
    });
  } catch (error) {
    console.error("Failed to fetch audits:", error);

    return Response.json(
      {
        success: false,
        message: "Unable to fetch audit history.",
      },
      { status: 500 }
    );
  }
}