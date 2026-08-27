"use client";

import React, { useCallback, useRef, useState } from "react";
import {
  ShieldCheck,
  UploadCloud,
  Camera,
  Image as ImageIcon,
  CheckCircle2,
  XCircle,
  FileWarning,
  RotateCcw,
  ScanLine,
} from "lucide-react";

// Point directly to FastAPI or fallback to local env
const API_ENDPOINT = process.env.NEXT_PUBLIC_API_URL || "/api/scan";

function StatusPill({ status }) {
  if (status === "PASS") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-sm border border-emerald-900 bg-emerald-950/60 px-2 py-0.5 text-xs font-medium text-emerald-400">
        <CheckCircle2 className="h-3.5 w-3.5" strokeWidth={2.25} />
        PASS
      </span>
    );
  }
  if (status === "FAIL") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-sm border border-red-900 bg-red-950/60 px-2 py-0.5 text-xs font-medium text-red-400">
        <XCircle className="h-3.5 w-3.5" strokeWidth={2.25} />
        FAIL
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-sm border border-neutral-700 bg-neutral-900 px-2 py-0.5 text-xs font-medium text-neutral-400">
      N/A
    </span>
  );
}

function FieldRow({ label, value }) {
  return (
    <div className="flex items-center justify-between border-b border-neutral-900 py-2.5 last:border-b-0">
      <span className="text-xs uppercase tracking-wide text-neutral-500">{label}</span>
      {value !== null && value !== undefined ? (
        <span className="font-mono text-sm text-neutral-100">{String(value)}</span>
      ) : (
        <span className="font-mono text-sm text-neutral-600">— not found</span>
      )}
    </div>
  );
}

function ResultsSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-9 w-32 rounded-sm bg-neutral-900" />
      <div className="rounded-sm border border-neutral-800 bg-neutral-950 p-4">
        <div className="mb-3 h-3 w-24 rounded-sm bg-neutral-900" />
        <div className="space-y-3">
          <div className="h-3 w-full rounded-sm bg-neutral-900" />
          <div className="h-3 w-5/6 rounded-sm bg-neutral-900" />
          <div className="h-3 w-2/3 rounded-sm bg-neutral-900" />
        </div>
      </div>
      <div className="rounded-sm border border-neutral-800 bg-neutral-950 p-4">
        <div className="mb-3 h-3 w-28 rounded-sm bg-neutral-900" />
        <div className="space-y-2.5">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-8 w-full rounded-sm bg-neutral-900" />
          ))}
        </div>
      </div>
    </div>
  );
}

export default function Page() {
  const [previewUrl, setPreviewUrl] = useState(null);
  const [fileName, setFileName] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);

  const submitScan = useCallback(async (file) => {
    setError(null);
    setResult(null);
    setLoading(true);

    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
    setFileName(file.name);

    try {
      const formData = new FormData();
      // "file" matches FastAPI UploadFile parameter name
      formData.append("file", file);

      const res = await fetch(API_ENDPOINT, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Scan failed — server returned ${res.status}`);
      }

      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not reach the scan service. Check the API connection and try again."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) submitScan(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) submitScan(file);
  };

  const reset = () => {
    setPreviewUrl(null);
    setFileName(null);
    setResult(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (cameraInputRef.current) cameraInputRef.current.value = "";
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100">
      {/* Navbar */}
      <nav className="flex h-14 items-center justify-between border-b border-neutral-800 bg-neutral-950 px-6">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-sm border border-neutral-700 bg-neutral-900">
            <ShieldCheck className="h-4 w-4 text-blue-400" strokeWidth={2} />
          </div>
          <span className="text-sm font-semibold tracking-tight text-neutral-100">
            LabelCheck
          </span>
          <span className="ml-1 rounded-sm border border-neutral-800 bg-neutral-900 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-neutral-500">
            Beta
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs text-neutral-500">
          <span className="hidden sm:inline">Legal Metrology (Packaged Commodities) Rules, 2011</span>
          <div className="flex items-center gap-1.5 rounded-sm border border-neutral-800 px-2 py-1">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span className="text-neutral-400">API online</span>
          </div>
        </div>
      </nav>

      {/* Main split layout */}
      <main className="mx-auto grid max-w-7xl grid-cols-1 gap-6 p-6 lg:grid-cols-[420px_1fr]">
        {/* Left: Ingestion Zone */}
        <section className="space-y-4">
          <div>
            <h1 className="text-sm font-semibold text-neutral-100">Scan a label</h1>
            <p className="mt-1 text-xs text-neutral-500">
              Upload a package image or capture one with your camera.
            </p>
          </div>

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            className={`relative flex min-h-70 flex-col items-center justify-center rounded-sm border border-dashed p-8 text-center transition-colors ${
              isDragging
                ? "border-blue-500 bg-blue-950/20"
                : "border-neutral-800 bg-neutral-950 hover:border-neutral-700"
            }`}
          >
            {previewUrl ? (
              <div className="flex w-full flex-col items-center gap-4">
                <img
                  src={previewUrl}
                  alt="Uploaded label preview"
                  className="max-h-52 w-full rounded-sm border border-neutral-800 object-contain"
                />
                <div className="flex w-full items-center justify-between gap-2 text-xs">
                  <span className="truncate text-neutral-500">{fileName}</span>
                  <button
                    onClick={reset}
                    className="flex items-center gap-1 rounded-sm border border-neutral-800 px-2 py-1 text-neutral-400 transition-colors hover:border-neutral-700 hover:text-neutral-200"
                  >
                    <RotateCcw className="h-3 w-3" />
                    Reset
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-sm border border-neutral-800 bg-neutral-900">
                  <ScanLine className="h-5 w-5 text-neutral-500" strokeWidth={1.75} />
                </div>
                <p className="mb-1 text-sm font-medium text-neutral-300">
                  Drop an image here
                </p>
                <p className="mb-6 text-xs text-neutral-600">
                  PNG or JPG · up to 10MB
                </p>
                <div className="flex w-full flex-col gap-2 sm:flex-row">
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="flex flex-1 items-center justify-center gap-2 rounded-sm border border-neutral-700 bg-neutral-900 px-4 py-2 text-xs font-medium text-neutral-200 transition-colors hover:border-neutral-600 hover:bg-neutral-800"
                  >
                    <UploadCloud className="h-3.5 w-3.5" />
                    Upload file
                  </button>
                  <button
                    onClick={() => cameraInputRef.current?.click()}
                    className="flex flex-1 items-center justify-center gap-2 rounded-sm border border-blue-800 bg-blue-950/40 px-4 py-2 text-xs font-medium text-blue-300 transition-colors hover:border-blue-700 hover:bg-blue-950/60"
                  >
                    <Camera className="h-3.5 w-3.5" />
                    Use camera
                  </button>
                </div>
              </>
            )}

            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              className="hidden"
            />
            <input
              ref={cameraInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>

          {previewUrl && !loading && (
            <button
              onClick={() => {
                if (fileInputRef.current?.files?.[0]) {
                  submitScan(fileInputRef.current.files[0]);
                } else if (cameraInputRef.current?.files?.[0]) {
                  submitScan(cameraInputRef.current.files[0]);
                }
              }}
              className="flex w-full items-center justify-center gap-2 rounded-sm border border-neutral-700 bg-neutral-100 px-4 py-2.5 text-xs font-semibold text-neutral-950 transition-colors hover:bg-white"
            >
              <ImageIcon className="h-3.5 w-3.5" />
              Re-run scan
            </button>
          )}

          <div className="rounded-sm border border-neutral-800 bg-neutral-950 p-4">
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
              What gets checked
            </h2>
            <ul className="space-y-1.5 text-xs text-neutral-500">
              <li>— Manufacturer / packer / importer details</li>
              <li>— Net quantity declaration</li>
              <li>— Maximum retail price (MRP)</li>
              <li>— Month & year of manufacture</li>
              <li>— Font size / readability (Rule 9)</li>
            </ul>
          </div>
        </section>

        {/* Right: Results Panel */}
        <section>
          {loading && <ResultsSkeleton />}

          {!loading && error && (
            <div className="flex min-h-70 flex-col items-center justify-center rounded-sm border border-red-950 bg-red-950/10 p-8 text-center">
              <FileWarning className="mb-3 h-6 w-6 text-red-500" strokeWidth={1.75} />
              <p className="mb-1 text-sm font-medium text-red-400">Scan failed</p>
              <p className="max-w-sm text-xs text-neutral-500">{error}</p>
            </div>
          )}

          {!loading && !error && !result && (
            <div className="flex min-h-70 flex-col items-center justify-center rounded-sm border border-neutral-800 p-8 text-center">
              <ShieldCheck className="mb-3 h-6 w-6 text-neutral-700" strokeWidth={1.5} />
              <p className="text-sm font-medium text-neutral-500">No scan yet</p>
              <p className="mt-1 text-xs text-neutral-600">
                Results will appear here once a label is submitted.
              </p>
            </div>
          )}

          {!loading && !error && result && (
            <div className="space-y-4">
              {/* Verdict badge */}
              <div className="flex items-center justify-between">
                {result.verdict === "PASS" || result.verdict === "COMPLIANT" ? (
                  <span className="inline-flex items-center gap-2 rounded-sm border border-emerald-800 bg-emerald-950/50 px-3 py-1.5 text-sm font-semibold text-emerald-400">
                    <CheckCircle2 className="h-4 w-4" strokeWidth={2.25} />
                    COMPLIANT
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-2 rounded-sm border border-red-800 bg-red-950/50 px-3 py-1.5 text-sm font-semibold text-red-400">
                    <XCircle className="h-4 w-4" strokeWidth={2.25} />
                    NON-COMPLIANT
                  </span>
                )}
                {typeof result.score === "number" && (
                  <span className="font-mono text-xs text-neutral-500">
                    score: <span className="text-neutral-300">{result.score}</span>
                  </span>
                )}
              </div>

              {/* Extracted fields card */}
              <div className="rounded-sm border border-neutral-800 bg-neutral-950">
                <div className="border-b border-neutral-900 px-4 py-2.5">
                  <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                    Extracted fields
                  </h2>
                </div>
                <div className="px-4 py-1">
                  <FieldRow label="MRP" value={result.extracted_fields?.mrp} />
                  <FieldRow label="Net Quantity" value={result.extracted_fields?.net_quantity || result.extracted_fields?.net_quantity_value} />
                  <FieldRow label="Mfg. Date" value={result.extracted_fields?.manufacture_date || result.extracted_fields?.mfg_date} />
                  <FieldRow label="Manufacturer" value={result.extracted_fields?.manufacturer || result.extracted_fields?.manufacturer_name} />
                </div>
              </div>

              {/* Rule checks table */}
              <div className="rounded-sm border border-neutral-800 bg-neutral-950">
                <div className="border-b border-neutral-900 px-4 py-2.5">
                  <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                    Rule checks
                  </h2>
                </div>
                <div className="divide-y divide-neutral-900">
                  {(result.rule_checks || result.checks || []).map((check, idx) => (
                    <div key={idx} className="flex items-start justify-between gap-4 px-4 py-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs text-neutral-500">
                            {check.rule_id || check.rule_name || `Rule ${idx + 1}`}
                          </span>
                          <span className="text-sm font-medium text-neutral-200">
                            {check.title || check.details || ""}
                          </span>
                        </div>
                        {check.detail && <p className="mt-1 text-xs text-neutral-500">{check.detail}</p>}
                      </div>
                      <StatusPill status={check.status} />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}