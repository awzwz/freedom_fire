"use client";

import Link from "next/link";
import { useState, useMemo } from "react";
import type { Ticket } from "@/lib/api";

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

interface Props {
  tickets: Ticket[];
}

export default function TicketTable({ tickets }: Props) {
  const [typeFilter, setTypeFilter] = useState("");
  const [segmentFilter, setSegmentFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const ticketTypes = useMemo(
    () => Array.from(new Set(tickets.map((t) => t.analytics?.ticket_type).filter(Boolean))),
    [tickets]
  );
  const segments = useMemo(
    () => Array.from(new Set(tickets.map((t) => t.segment))),
    [tickets]
  );

  const filtered = useMemo(() => {
    return tickets.filter((t) => {
      if (typeFilter && t.analytics?.ticket_type !== typeFilter) return false;
      if (segmentFilter && t.segment !== segmentFilter) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const searchable = [
          t.guid, t.description, t.city, t.assignment?.manager_name, t.assignment?.office_name,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        if (!searchable.includes(q)) return false;
      }
      return true;
    });
  }, [tickets, typeFilter, segmentFilter, searchQuery]);

  return (
    <>
      <div className="filters">
        <div style={{ position: "relative" }}>
          <svg
            width="16" height="16" viewBox="0 0 24 24"
            fill="none" stroke="var(--text-muted)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", pointerEvents: "none" }}
          >
            <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            placeholder="Search tickets..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ paddingLeft: 36 }}
          />
        </div>
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
          <option value="">All Types</option>
          {ticketTypes.map((t) => (
            <option key={t} value={t!}>{t}</option>
          ))}
        </select>
        <select value={segmentFilter} onChange={(e) => setSegmentFilter(e.target.value)}>
          <option value="">All Segments</option>
          {segments.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <span className="badge badge-primary" style={{ alignSelf: "center" }}>
          {filtered.length} / {tickets.length}
        </span>
      </div>

      <div className="card table-wrap" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Segment</th>
              <th>City</th>
              <th>Type</th>
              <th>Sentiment</th>
              <th>Priority</th>
              <th>Language</th>
              <th>Manager</th>
              <th>Office</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={10} style={{ textAlign: "center", padding: 40, color: "var(--text-secondary)" }}>
                  No tickets match your filters.
                </td>
              </tr>
            ) : (
              filtered.map((t) => (
                <tr key={t.id}>
                  <td>
                    <Link href={`/tickets/${t.id}`} style={{ fontWeight: 600, fontFamily: "monospace", fontSize: 13 }}>
                      {t.guid.slice(0, 12)}
                    </Link>
                  </td>
                  <td>
                    <span className={`badge ${SEGMENT_BADGE[t.segment] || "badge-gray"}`}>
                      {t.segment}
                    </span>
                  </td>
                  <td>{t.city || "—"}</td>
                  <td style={{ fontSize: 13 }}>{t.analytics?.ticket_type || "—"}</td>
                  <td>
                    {t.analytics ? (
                      <span className={`badge ${SENTIMENT_BADGE[t.analytics.sentiment] || "badge-gray"}`}>
                        {t.analytics.sentiment}
                      </span>
                    ) : "—"}
                  </td>
                  <td>
                    {t.analytics ? (
                      <span className={`badge ${t.analytics.priority_score >= 8 ? "badge-red" : t.analytics.priority_score >= 5 ? "badge-yellow" : "badge-green"}`}>
                        {t.analytics.priority_score}
                      </span>
                    ) : "—"}
                  </td>
                  <td style={{ fontSize: 13 }}>{t.analytics?.language || "—"}</td>
                  <td style={{ fontSize: 13 }}>{t.assignment?.manager_name || "—"}</td>
                  <td style={{ fontSize: 13 }}>{t.assignment?.office_name || "—"}</td>
                  <td>
                    {t.assignment ? (
                      <span className="badge badge-dot badge-green">Assigned</span>
                    ) : t.analytics ? (
                      <span className="badge badge-dot badge-yellow">Analyzed</span>
                    ) : (
                      <span className="badge badge-dot badge-gray">Pending</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
