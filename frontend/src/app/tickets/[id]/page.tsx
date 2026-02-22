"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, type Ticket } from "@/lib/api";

/* ── Badge helpers ──────────────────────────────────────────────── */
const SENTIMENT_BADGE: Record<string, string> = {
  "Позитивный": "badge-green",
  "Нейтральный": "badge-gray",
  "Негативный": "badge-red",
};

const SEGMENT_BADGE: Record<string, string> = {
  VIP: "badge-yellow",
  Priority: "badge-primary",
  Mass: "badge-gray",
};

function getPriorityBadge(score: number): string {
  if (score >= 8) return "badge-red";
  if (score >= 5) return "badge-yellow";
  return "badge-green";
}

export default function TicketDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getTicket(id).then(setTicket).catch(console.error).finally(() => setLoading(false));
  }, [id]);

  /* ── Loading ────────────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="state-card">
        <div className="state-card-icon loading">
          <div className="spinner" />
        </div>
        <h3>Loading Ticket</h3>
        <p>Fetching ticket details...</p>
      </div>
    );
  }

  /* ── Not found ──────────────────────────────────────────────── */
  if (!ticket) {
    return (
      <div className="state-card">
        <div className="state-card-icon error">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
          </svg>
        </div>
        <h3>Ticket Not Found</h3>
        <p>The requested ticket could not be loaded.</p>
        <div style={{ marginTop: 16 }}>
          <Link href="/" className="btn btn-outline">Back to Tickets</Link>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* ── Header with GUID + back button + status pills ────── */}
      <div className="page-header">
        <div>
          <h1 style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--primary-600)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z" />
              <polyline points="14,2 14,8 20,8" />
            </svg>
            Ticket
          </h1>
          <p className="page-header-subtitle" style={{ fontFamily: "monospace", fontSize: 13 }}>
            {ticket.guid}
          </p>
        </div>
        <Link href="/" className="btn btn-outline">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" />
          </svg>
          Back to list
        </Link>
      </div>

      {/* ── Status pills ─────────────────────────────────────── */}
      <div className="pills-row" style={{ marginBottom: 24 }}>
        <span className={`badge badge-dot ${SEGMENT_BADGE[ticket.segment] || "badge-gray"}`}>
          {ticket.segment}
        </span>
        {ticket.analytics && (
          <>
            <span className={`badge badge-dot ${SENTIMENT_BADGE[ticket.analytics.sentiment] || "badge-gray"}`}>
              {ticket.analytics.sentiment}
            </span>
            <span className={`badge badge-dot ${getPriorityBadge(ticket.analytics.priority_score)}`}>
              Priority: {ticket.analytics.priority_score}
            </span>
            <span className="badge badge-dot badge-primary">
              {ticket.analytics.language}
            </span>
            <span className="badge badge-gray">
              {ticket.analytics.ticket_type}
            </span>
          </>
        )}
        {ticket.assignment && (
          <span className="badge badge-dot badge-green">Assigned</span>
        )}
        {!ticket.analytics && !ticket.assignment && (
          <span className="badge badge-dot badge-gray">Pending</span>
        )}
      </div>

      <div className="detail-grid">
        {/* ── Left column ──────────────────────────────────────── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div className="card">
            <div className="detail-section">
              <h3>Client Info</h3>
              <Row label="GUID" value={ticket.guid} mono />
              <Row label="Segment" value={ticket.segment} />
              <Row label="Gender" value={ticket.gender} />
              <Row label="Birth Date" value={ticket.birth_date} />
            </div>

            <div className="detail-section">
              <h3>Address</h3>
              <Row label="Country" value={ticket.country} />
              <Row label="Region" value={ticket.region} />
              <Row label="City" value={ticket.city} />
              <Row label="Street" value={ticket.street} />
              <Row label="Building" value={ticket.building} />
              <Row label="Geo Status" value={ticket.geo_status} />
              {ticket.client_lat && (
                <Row label="Coordinates" value={`${ticket.client_lat}, ${ticket.client_lon}`} mono />
              )}
            </div>
          </div>

          <div className="card">
            <div className="detail-section">
              <h3>Description</h3>
              <div className="description-block">
                {ticket.description || "No description provided."}
              </div>
            </div>
          </div>
        </div>

        {/* ── Right column ─────────────────────────────────────── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {ticket.analytics && (
            <div className="ai-card">
              <div className="ai-card-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2a4 4 0 014 4c0 1.95-1.4 3.58-3.25 3.93" />
                  <path d="M8.56 13.44A4 4 0 0012 22a4 4 0 003.44-8.56" />
                  <path d="M14 2.5a2.5 2.5 0 010 5" /><path d="M10 2.5a2.5 2.5 0 000 5" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                AI Analysis
              </div>
              <div className="detail-section">
                <Row label="Ticket Type" value={ticket.analytics.ticket_type} />
                <Row label="Sentiment" value={ticket.analytics.sentiment} badge={SENTIMENT_BADGE[ticket.analytics.sentiment]} />
                <Row label="Priority" value={String(ticket.analytics.priority_score)} badge={getPriorityBadge(ticket.analytics.priority_score)} />
                <Row label="Language" value={ticket.analytics.language} />
                <Row label="LLM Model" value={ticket.analytics.llm_model} />
              </div>
              <div className="detail-section">
                <h3>Summary</h3>
                <p style={{ fontSize: 14, lineHeight: 1.7, color: "var(--text)" }}>
                  {ticket.analytics.summary}
                </p>
              </div>
            </div>
          )}

          {ticket.assignment && (
            <div className="assignment-card">
              <div className="detail-section">
                <h3>Assignment</h3>
                <Row label="Manager" value={ticket.assignment.manager_name} highlight />
                <Row label="Office" value={ticket.assignment.office_name} />
                <Row
                  label="Distance"
                  value={ticket.assignment.distance_km ? `${ticket.assignment.distance_km} km` : "N/A"}
                />
                <Row label="Reason" value={ticket.assignment.assignment_reason} />
              </div>
              {ticket.assignment.fallback_used && (
                <div className="fallback-tag">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                    <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
                  </svg>
                  Fallback routing was used
                </div>
              )}
              {!ticket.assignment.fallback_used && (
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 12, fontSize: 12, fontWeight: 600, color: "var(--success)" }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  Direct assignment
                </div>
              )}
            </div>
          )}

          {!ticket.analytics && !ticket.assignment && (
            <div className="state-card">
              <div className="state-card-icon empty">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M8 12h8" />
                </svg>
              </div>
              <h3>Not Processed Yet</h3>
              <p>This ticket has not been analyzed or assigned.</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

/* ── Row component ──────────────────────────────────────────────── */

function Row({
  label,
  value,
  mono,
  badge,
  highlight,
}: {
  label: string;
  value: string | null | undefined;
  mono?: boolean;
  badge?: string;
  highlight?: boolean;
}) {
  return (
    <div className="detail-row">
      <span className="label">{label}</span>
      {badge ? (
        <span className={`badge ${badge}`}>{value || "—"}</span>
      ) : (
        <span
          className="val"
          style={{
            fontFamily: mono ? "monospace" : undefined,
            fontWeight: highlight ? 600 : undefined,
            color: highlight ? "var(--primary-700)" : undefined,
          }}
        >
          {value || "—"}
        </span>
      )}
    </div>
  );
}
