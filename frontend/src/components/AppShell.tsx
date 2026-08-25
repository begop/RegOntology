import { useQuery } from "@tanstack/react-query";
import {
  BookOpenText,
  BotMessageSquare,
  ChevronDown,
  CircleUserRound,
  DatabaseZap,
  Home,
  Menu,
  Moon,
  Network,
  Search,
  ShieldCheck,
  Sun,
  X,
} from "lucide-react";
import { useState, type FormEvent } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAppContext } from "../context/AppContext";
import { getSystemStatus } from "../lib/api";
import { Badge } from "./ui";

const primaryNavigation = [
  { to: "/", label: "홈", icon: Home, end: true },
  { to: "/regulations", label: "규정 라이브러리", icon: BookOpenText },
  { to: "/qa", label: "규정 QA", icon: BotMessageSquare },
  { to: "/ontology", label: "Ontology Explorer", icon: Network },
];

const adminNavigation = [{ to: "/admin/ingestions", label: "수집 및 운영", icon: DatabaseZap }];

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [search, setSearch] = useState("");
  const { asOf, setAsOf, theme, toggleTheme } = useAppContext();
  const navigate = useNavigate();
  const location = useLocation();
  const statusQuery = useQuery({ queryKey: ["system-status"], queryFn: getSystemStatus, staleTime: 60_000, retry: false });

  function handleSearch(event: FormEvent) {
    event.preventDefault();
    const query = search.trim();
    navigate(query ? `/regulations?q=${encodeURIComponent(query)}` : "/regulations");
    setMobileOpen(false);
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? "sidebar--open" : ""}`} aria-label="주 탐색">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true"><ShieldCheck /></span>
          <div><strong>RegOntology</strong><span>Regulation Intelligence</span></div>
          <button className="icon-button sidebar__close" onClick={() => setMobileOpen(false)} aria-label="메뉴 닫기"><X /></button>
        </div>

        <nav className="sidebar-nav">
          <p className="nav-group-label">Workspace</p>
          {primaryNavigation.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} onClick={() => setMobileOpen(false)} className={({ isActive }) => `nav-item ${isActive ? "nav-item--active" : ""}`}>
              <Icon aria-hidden="true" /><span>{label}</span>
            </NavLink>
          ))}
          <p className="nav-group-label nav-group-label--spaced">Curator</p>
          {adminNavigation.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} onClick={() => setMobileOpen(false)} className={({ isActive }) => `nav-item ${isActive ? "nav-item--active" : ""}`}>
              <Icon aria-hidden="true" /><span>{label}</span><Badge tone="neutral">관리</Badge>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar__footer">
          <div className="publication-status">
            <span className={`status-dot ${statusQuery.data?.graph === "healthy" ? "status-dot--ok" : "status-dot--warning"}`} />
            <div>
              <span>Knowledge snapshot</span>
              <strong>{statusQuery.data?.graph === "healthy" ? "동기화됨" : "확인 중"}</strong>
            </div>
          </div>
          <div className="sidebar-mock"><DatabaseZap aria-hidden="true" /><span>Mock workspace</span></div>
        </div>
      </aside>
      {mobileOpen ? <button className="sidebar-backdrop" aria-label="메뉴 닫기" onClick={() => setMobileOpen(false)} /> : null}

      <div className="app-frame">
        <header className="topbar">
          <button className="icon-button mobile-menu" onClick={() => setMobileOpen(true)} aria-label="메뉴 열기"><Menu /></button>
          <form className="global-search" onSubmit={handleSearch} role="search">
            <Search aria-hidden="true" />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="규정명, 조문, 통제 검색" aria-label="통합 규정 검색" />
            <kbd>↵</kbd>
          </form>
          <div className="topbar__context">
            <label className="date-control">
              <span>적용 기준일</span>
              <input type="date" value={asOf} onChange={(event) => setAsOf(event.target.value)} />
            </label>
            <button className="icon-button" onClick={toggleTheme} aria-label={theme === "light" ? "어두운 테마로 전환" : "밝은 테마로 전환"}>
              {theme === "light" ? <Moon /> : <Sun />}
            </button>
            <button className="user-menu" aria-label="사용자 메뉴">
              <span className="avatar"><CircleUserRound /></span>
              <span><strong>김준법</strong><small>Compliance</small></span>
              <ChevronDown aria-hidden="true" />
            </button>
          </div>
        </header>

        <main id="main-content" className={`main-content route-${location.pathname.split("/")[1] || "home"}`} tabIndex={-1}>
          <Outlet />
        </main>
        <footer className="app-footer">
          <span>RegOntology · 근거 우선 규정 탐색</span>
          <span>본 서비스의 답변은 참고용이며 최종 판단은 담당 부서에 확인하세요.</span>
        </footer>
      </div>
    </div>
  );
}
