import { getServerSession } from "next-auth";

import { authOptions } from "@/auth";
import connectDb from "@/lib/mongodb";
import Audit from "@/models/Audit";

const PYTHON_API_URL = process.env.PYTHON_API_URL;

export async function POST(request) {
    try {
        // ---------------------------------------------------------
        // 1. Authentication
        // ---------------------------------------------------------

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

        // ---------------------------------------------------------
        // 2. Validate configuration
        // ---------------------------------------------------------

        if (!PYTHON_API_URL) {
            console.error("PYTHON_API_URL is not configured.");

            return Response.json(
                {
                    success: false,
                    message: "Scan service is not configured.",
                },
                { status: 500 }
            );
        }

        // ---------------------------------------------------------
        // 3. Get uploaded image
        // ---------------------------------------------------------

        const formData = await request.formData();
        const file = formData.get("file");

        if (!file || typeof file === "string") {
            return Response.json(
                {
                    success: false,
                    message: "An image file is required.",
                },
                { status: 400 }
            );
        }

        if (!file.type || !file.type.startsWith("image/")) {
            return Response.json(
                {
                    success: false,
                    message: "Only image uploads are supported.",
                },
                { status: 415 }
            );
        }

        // ---------------------------------------------------------
        // 4. Forward image to Python scan service
        // ---------------------------------------------------------

        const pythonFormData = new FormData();

        pythonFormData.append(
            "file",
            file,
            file.name || "scan-image"
        );

        const pythonResponse = await fetch(
            `${PYTHON_API_URL}/api/v1/scan`,
            {
                method: "POST",
                body: pythonFormData,
            }
        );

        let pythonResult;

        try {
            pythonResult = await pythonResponse.json();
        } catch {
            pythonResult = null;
        }

        if (!pythonResponse.ok) {
            console.error(
                "Python scan service returned an error:",
                pythonResponse.status,
                pythonResult
            );

            return Response.json(
                {
                    success: false,
                    message:
                        pythonResult?.detail ||
                        "Unable to analyze the uploaded image.",
                },
                { status: pythonResponse.status }
            );
        }

        // ---------------------------------------------------------
        // 5. Validate scan result
        // ---------------------------------------------------------

        if (
            !pythonResult ||
            !pythonResult.verdict ||
            !pythonResult.extracted_fields
        ) {
            console.error(
                "Invalid response from Python scan service:",
                pythonResult
            );

            return Response.json(
                {
                    success: false,
                    message: "Scan service returned an invalid result.",
                },
                { status: 502 }
            );
        }

        // ---------------------------------------------------------
        // 6. Create audit record
        // ---------------------------------------------------------

        await connectDb();

        const scanId = crypto.randomUUID();

        const audit = await Audit.create({
            userId: session.user.id,

            scan_id: scanId,

            timestamp: pythonResult.timestamp
                ? new Date(pythonResult.timestamp)
                : new Date(),

            verdict: pythonResult.verdict,

            px_per_mm: pythonResult.px_per_mm,

            extracted_fields: pythonResult.extracted_fields,

            rule_checks: pythonResult.rule_checks || [],

            extraction_confidence:
                pythonResult.extraction_confidence || {},

            extraction_evidence:
                pythonResult.extraction_evidence || {},

            ruleset_version:
                pythonResult.ruleset_version || "1.0.0",

            calibration_fallback:
                pythonResult.calibration_fallback || false,

            barcode_data:
                pythonResult.barcode_data || null,
        });
        // ---------------------------------------------------------
        // 7. Return result
        // ---------------------------------------------------------

        return Response.json(
            {
                success: true,
                scan_id: scanId,
                verdict: pythonResult.verdict,
                timestamp: audit.timestamp,
                extracted_fields: audit.extracted_fields,
                rule_checks: audit.rule_checks,
            },
            { status: 201 }
        );
    } catch (error) {
        console.error("Scan API error:", error);

        return Response.json(
            {
                success: false,
                message: "Unable to complete scan.",
            },
            { status: 500 }
        );
    }
}