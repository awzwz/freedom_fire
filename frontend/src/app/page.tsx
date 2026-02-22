"use client";

import { useEffect, useState } from "react";
import { api, type Ticket } from "@/lib/api";
import TicketTable from "@/components/TicketTable";

export default function TicketsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadTickets = async () => {
    setLoading(true);
    try {
      const data = await api.getTickets();
      setTickets(data.tickets);
    } catch (e: any) {
      setMessage(`Error loading tickets: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadTickets(); }, []);

  const handleIngest = async () => {
    setProcessing(true);
    setMessage(null);
    try {
      const result = await api.ingestCsv();
      setMessage(`Ingested: ${JSON.stringify(result.counts)}`);
      await loadTickets();
    } catch (e: any) {
      setMessage(`Ingest error: ${e.message}`);
    } finally {
      setProcessing(false);
    }
  };

  const handleProcess = async () => {
    setProcessing(true);
    setMessage(null);
    try {
      const result = await api.processAll();
      setMessage(`Processed ${result.total_processed} tickets: ${result.successful} OK, ${result.failed} failed`);
      await loadTickets();
    } catch (e: any) {
      setMessage(`Process error: ${e.message}`);
    } finally {
      setProcessing(false);
    }
  };

  return (
    <>
      <div className="page-header">
        <h1>Tickets</h1>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-outline" onClick={handleIngest} disabled={processing}>
            {processing ? "..." : "Ingest CSV"}
          </button>
          <button className="btn btn-primary" onClick={handleProcess} disabled={processing}>
            {processing && (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ animation: "spin 0.8s linear infinite" }}>
                <path d="M21 12a9 9 0 11-6.219-8.56" />
              </svg>
            )}
            {processing ? "Processing..." : "Process All"}
          </button>
        </div>
      </div>

      {message && (
        <div className="message-card">
          {message}
        </div>
      )}

      {loading ? (
        <div className="state-card">
          <div className="state-card-icon loading">
            <div className="spinner" />
          </div>
          <h3>Loading Tickets</h3>
          <p>Fetching ticket data...</p>
        </div>
      ) : tickets.length === 0 ? (
        <div className="state-card">
          <div className="state-card-icon empty">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z" />
              <polyline points="14,2 14,8 20,8" />
            </svg>
          </div>
          <h3>No Tickets Yet</h3>
          <p>Ingest or upload tickets to get started.</p>
        </div>
      ) : (
        <TicketTable tickets={tickets} />
      )}
    </>
  );
}
