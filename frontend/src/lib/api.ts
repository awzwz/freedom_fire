const API_BASE = "/api";

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// ─── Types ──────────────────────────────────────────────────────────

export interface TicketAnalytics {
  ticket_type: string;
  sentiment: string;
  priority_score: number;
  language: string;
  summary: string;
  llm_model: string | null;
}

export interface TicketAssignment {
  manager_name: string | null;
  manager_id: number;
  office_name: string | null;
  office_id: number;
  distance_km: number | null;
  fallback_used: boolean;
  assignment_reason: string | null;
}

export interface Ticket {
  id: number;
  guid: string;
  gender: string | null;
  birth_date: string | null;
  description: string | null;
  attachments: string | null;
  segment: string;
  country: string | null;
  region: string | null;
  city: string | null;
  street: string | null;
  building: string | null;
  client_lat: number | null;
  client_lon: number | null;
  geo_status: string;
  created_at: string | null;
  analytics: TicketAnalytics | null;
  assignment: TicketAssignment | null;
}

export interface TicketsResponse {
  total: number;
  tickets: Ticket[];
}

export interface AnalyticsSummary {
  total_tickets: number;
  processed: number;
  assigned: number;
  unprocessed: number;
  by_type: Record<string, number>;
  by_sentiment: Record<string, number>;
  by_language: Record<string, number>;
  by_segment: Record<string, number>;
  by_office: Record<string, number>;
  fallback_count: number;
}

export interface ManagerLoad {
  id: number;
  name: string;
  position: string;
  current_load: number;
  office_name: string;
}

export interface ManagersResponse {
  total_managers: number;
  managers: ManagerLoad[];
}

export interface ProcessResult {
  status: string;
  total_processed: number;
  successful: number;
  failed: number;
  results: Array<{
    ticket_id: number;
    ticket_guid: string;
    assigned_manager: string | null;
    assigned_office: string | null;
    distance_km: number | null;
    fallback_used: boolean;
    error: string | null;
  }>;
}

export interface ChartItem {
  name: string;
  value: number;
}

export interface ChartPayload {
  type: string;
  title: string;
  data: ChartItem[];
}

export interface AssistantResponse {
  answer: string;
  chart: ChartPayload | null;
}

// ─── API calls ──────────────────────────────────────────────────────

export const api = {
  getTickets: () => fetchApi<TicketsResponse>("/tickets"),
  getTicket: (id: number) => fetchApi<Ticket>(`/tickets/${id}`),
  getSummary: () => fetchApi<AnalyticsSummary>("/analytics/summary"),
  getManagers: () => fetchApi<ManagersResponse>("/analytics/managers"),
  ingestCsv: () => fetchApi<{ status: string; counts: Record<string, number> }>("/process/ingest", { method: "POST" }),
  processAll: () => fetchApi<ProcessResult>("/process", { method: "POST" }),
  processSingle: (id: number) => fetchApi<ProcessResult>(`/process/${id}`, { method: "POST" }),
  askAssistant: (question: string) =>
    fetchApi<AssistantResponse>("/analytics/assistant", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
};
