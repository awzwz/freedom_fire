"use client";

import React, { useEffect, useState } from "react";
import { api, type AnalyticsSummary, type ManagerLoad } from "@/lib/api";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import UploadTickets from "@/components/UploadTickets";

/* ── Chart palette (green-forward) ──────────────────────────────── */
const PIE_COLORS = ["#059669", "#10b981", "#34d399", "#6ee7b7", "#a7f3d0", "#047857", "#064e3b"];
const SENTIMENT_COLORS: Record<string, string> = {
  "Позитивный": "#059669",
  "Негативный": "#9f1239",
  "Нейтральный": "#94a3b8",
};

/* ── Custom tooltip ─────────────────────────────────────────────── */
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      {label && <div className="chart-tooltip-label">{label}</div>}
      {payload.map((p: any, i: number) => (
        <div key={i} className="chart-tooltip-value" style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 2 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: p.fill || p.color, display: "inline-block", flexShrink: 0 }} />
          <span>{p.name || p.dataKey}: <strong style={{ color: "var(--text)" }}>{p.value}</strong></span>
        </div>
      ))}
    </div>
  );
}

/* ── Stat icon SVGs ─────────────────────────────────────────────── */
function TicketIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z" />
      <polyline points="14,2 14,8 20,8" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function UsersIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" /><circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 00-3-3.87" /><path d="M16 3.13a4 4 0 010 7.75" />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function FallbackIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [managers, setManagers] = useState<ManagerLoad[]>([]);
  const [loading, setLoading] = useState(true);

  const refreshData = () => {
    setLoading(true);
    Promise.all([api.getSummary(), api.getManagers()])
      .then(([s, m]) => { setSummary(s); setManagers(m.managers); })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refreshData();
  }, []);

  /* ── Loading state ──────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="state-card">
        <div className="state-card-icon loading">
          <div className="spinner" />
        </div>
        <h3>Loading Dashboard</h3>
        <p>Fetching analytics and manager data...</p>
      </div>
    );
  }

  /* ── Empty state ────────────────────────────────────────────── */
  if (!summary) {
    return (
      <>
        <UploadTickets onUploadSuccess={refreshData} />
        <div className="state-card">
          <div className="state-card-icon empty">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z" />
              <polyline points="14,2 14,8 20,8" />
            </svg>
          </div>
          <h3>No Data Available</h3>
          <p>Upload tickets to see analytics and insights.</p>
        </div>
      </>
    );
  }

  /* ── Chart data ─────────────────────────────────────────────── */
  const typeData = Object.entries(summary.by_type).map(([name, value]) => ({ name, value }));
  const sentimentData = Object.entries(summary.by_sentiment).map(([name, value]) => ({ name, value }));
  const officeData = Object.entries(summary.by_office).map(([name, value]) => ({ name, value }));
  const managerData = managers.slice(0, 20).map((m) => ({
    name: m.name.length > 15 ? m.name.slice(0, 15) + "..." : m.name,
    fullName: m.name,
    load: m.current_load,
    office: m.office_name,
  }));

  const stats = [
    { label: "Total Tickets", value: summary.total_tickets, icon: <TicketIcon /> },
    { label: "Processed", value: summary.processed, icon: <CheckIcon /> },
    { label: "Assigned", value: summary.assigned, icon: <UsersIcon /> },
    { label: "Unprocessed", value: summary.unprocessed, icon: <AlertIcon /> },
    { label: "Fallback Used", value: summary.fallback_count, icon: <FallbackIcon /> },
  ];

  return (
    <>
      <UploadTickets onUploadSuccess={refreshData} />

      {/* ── Stat cards ─────────────────────────────────────────── */}
      <div className="stat-grid">
        {stats.map((s) => (
          <div className="stat-card" key={s.label}>
            <div className="stat-icon">{s.icon}</div>
            <div className="label">{s.label}</div>
            <div className="value">{s.value}</div>
          </div>
        ))}
      </div>

      {/* ── Charts ─────────────────────────────────────────────── */}
      <div className="chart-grid">
        <div className="chart-card">
          <h3>By Ticket Type</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={typeData} dataKey="value" nameKey="name" cx="50%" cy="45%" outerRadius={85} innerRadius={40} paddingAngle={2} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} style={{ fontSize: 12 }}>
                {typeData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>By Sentiment</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={sentimentData} dataKey="value" nameKey="name" cx="50%" cy="45%" outerRadius={85} innerRadius={40} paddingAngle={2} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} style={{ fontSize: 12 }}>
                {sentimentData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={SENTIMENT_COLORS[entry.name] || "#94a3b8"} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Assignments by Office</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={officeData}>
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: "var(--text-secondary)" }} angle={-20} textAnchor="end" height={60} interval={0} />
              <YAxis tick={{ fontSize: 11, fill: "var(--text-secondary)" }} />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(5, 150, 105, 0.06)" }} />
              <Bar dataKey="value" fill="#059669" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Manager Load (Top 20)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={managerData} layout="vertical">
              <XAxis type="number" tick={{ fontSize: 11, fill: "var(--text-secondary)" }} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 11, fill: "var(--text-secondary)" }} width={120} interval={0} />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(5, 150, 105, 0.06)" }} />
              <Bar dataKey="load" fill="#10b981" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Manager table ──────────────────────────────────────── */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">All Managers</h3>
          <span className="badge badge-primary">{managers.length} total</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Position</th>
                <th>Office</th>
                <th>Current Load</th>
              </tr>
            </thead>
            <tbody>
              {managers.map((m) => (
                <tr key={m.id}>
                  <td style={{ fontWeight: 500 }}>{m.name}</td>
                  <td>{m.position}</td>
                  <td>{m.office_name}</td>
                  <td>
                    <span className={`badge ${m.current_load > 10 ? "badge-red" : m.current_load > 5 ? "badge-yellow" : "badge-green"}`}>
                      {m.current_load}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
