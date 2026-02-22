"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import "./globals.css";
import AiAssistant from "@/components/AiAssistant";

function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2L3 7v6c0 5.25 3.75 10.13 9 11.25C17.25 23.13 21 18.25 21 13V7l-9-5z" />
          </svg>
        </div>
        <div className="sidebar-logo-text">Freedom <span>Fire</span></div>
      </div>

      <div className="sidebar-section-label">Navigation</div>

      <nav className="sidebar-nav">
        <Link
          href="/dashboard"
          className={`sidebar-link ${pathname === "/dashboard" ? "active" : ""}`}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" />
            <rect x="14" y="14" width="7" height="7" rx="1" />
          </svg>
          Dashboard
        </Link>
        <Link
          href="/"
          className={`sidebar-link ${pathname === "/" || pathname.startsWith("/tickets") ? "active" : ""}`}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z" />
            <polyline points="14,2 14,8 20,8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
          Tickets
        </Link>
      </nav>

      <div className="sidebar-footer">
        FIRE v1.0 &mdash; Intelligent Routing
      </div>
    </aside>
  );
}

function Topbar() {
  const pathname = usePathname();

  const getTitle = () => {
    if (pathname === "/dashboard") return "Dashboard";
    if (pathname.startsWith("/tickets/")) return "Ticket Details";
    return "Tickets";
  };

  return (
    <header className="topbar">
      <span className="topbar-title">{getTitle()}</span>
      <div className="topbar-actions">
        <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
          Freedom Intelligent Routing Engine
        </span>
      </div>
    </header>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <head>
        <title>FIRE — Freedom Intelligent Routing Engine</title>
        <meta name="description" content="Ticket processing and smart assignment dashboard" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <div className="app-shell">
          <Sidebar />
          <Topbar />
          <main className="main-content">
            <div className="container">{children}</div>
          </main>
        </div>
        <AiAssistant />
      </body>
    </html>
  );
}
