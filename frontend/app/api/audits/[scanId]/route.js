import { getServerSession } from "next-auth";

import { authOptions } from "@/auth";
import connectDb from "@/lib/mongodb";
import Audit from "@/models/Audit";

export async function GET(request, { params }) {
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

    const { scanId } = await params;

    if (!scanId) {
      return Response.json(
        {
          success: false,
          message: "Scan ID is required.",
        },
        { status: 400 }
      );
    }

    await connectDb();

    const audit = await Audit.findOne({
      scan_id: scanId,
      userId: session.user.id,
    }).lean();

    if (!audit) {
      return Response.json(
        {
          success: false,
          message: "Audit not found.",
        },
        { status: 404 }
      );
    }

    return Response.json({
      success: true,
      audit,
    });
  } catch (error) {
    console.error("Failed to fetch audit:", error);

    return Response.json(
      {
        success: false,
        message: "Unable to fetch audit.",
      },
      { status: 500 }
    );
  }
}