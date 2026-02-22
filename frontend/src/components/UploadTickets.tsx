"use client";

import React, { useState } from "react";

interface ProcessResult {
    message: string;
    processed?: {
        total_processed: number;
    };
}

export default function UploadTickets({ onUploadSuccess }: { onUploadSuccess: () => void }) {
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<ProcessResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile && (droppedFile.name.endsWith(".csv") || droppedFile.name.endsWith(".zip"))) {
            setFile(droppedFile);
            setError(null);
        } else {
            setError("Please drop a .csv or .zip file.");
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            setFile(e.target.files[0]);
            setError(null);
        }
    };

    const handleUpload = async () => {
        if (!file) return;
        setLoading(true);
        setResult(null);
        setError(null);

        const formData = new FormData();
        formData.append("file", file);

        try {
            const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8005";
            const response = await fetch(`${API_BASE}/api/process/upload`, {
                method: "POST",
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            const data = await response.json();
            setResult(data as ProcessResult);
            onUploadSuccess();
        } catch (err: unknown) {
            const errorMessage = err instanceof Error ? err.message : String(err);
            setError(errorMessage || "An error occurred during upload.");
        } finally {
            setLoading(false);
            setFile(null);
        }
    };

    return (
        <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-header">
                <h3 className="card-title">Upload Tickets</h3>
                <span className="badge badge-gray">CSV / ZIP</span>
            </div>

            <div
                className={`upload-zone ${file ? "has-file" : ""}`}
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
                onClick={() => document.getElementById("fileInput")?.click()}
            >
                <input
                    id="fileInput"
                    type="file"
                    accept=".csv,.zip"
                    style={{ display: "none" }}
                    onChange={handleFileChange}
                />
                <div className="upload-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                        <polyline points="17 8 12 3 7 8" />
                        <line x1="12" y1="3" x2="12" y2="15" />
                    </svg>
                </div>
                {file ? (
                    <p className="file-name">{file.name}</p>
                ) : (
                    <p>Drag & drop your .csv or .zip file here, or click to browse</p>
                )}
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16 }}>
                <button
                    className={`btn ${file && !loading ? "btn-primary" : "btn-outline"}`}
                    onClick={handleUpload}
                    disabled={!file || loading}
                    style={!file || loading ? { opacity: 0.5, cursor: "not-allowed" } : {}}
                >
                    {loading && (
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ animation: "spin 0.8s linear infinite" }}>
                            <path d="M21 12a9 9 0 11-6.219-8.56" />
                        </svg>
                    )}
                    {loading ? "Uploading & Processing..." : "Start Processing"}
                </button>

                {error && <span className="alert-error" style={{ padding: "8px 14px", fontSize: 13 }}>{error}</span>}
            </div>

            {result && (
                <div className="alert-success">
                    <strong>Success!</strong> {result.message}<br />
                    New records processed: {result.processed?.total_processed || 0} (Skipped duplicates automatically).
                </div>
            )}
        </div>
    );
}
