import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import type { School } from "../types";

const adminLinks = [
  ["/dashboard", "Dashboard"],
  ["/accounts", "Accounts"],
  ["/setup", "Setup wizard"],
  ["/classes", "Classes"],
  ["/sections", "Sections"],
  ["/subjects", "Subjects"],
  ["/teachers", "Teachers"],
  ["/rooms", "Rooms"],
  ["/periods", "Periods"],
  ["/rules", "Rules"],
  ["/timetable/generate", "Generate"],
  ["/timetable/master", "Master grid"],
  ["/timetable/classes", "Class views"],
  ["/timetable/teachers", "Teacher views"],
  ["/timetable/rooms", "Room views"],
  ["/timetable/editor", "Editor"],
  ["/ai-assistant", "AI assistant"],
  ["/import", "Excel import"],
  ["/settings", "Settings"],
];

export default function Layout() {
  const { session, logout, role, setActiveSchool } = useAuth();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const [schools, setSchools] = useState<School[]>([]);
  const links =
    role === "teacher"
      ? [
          ["/teacher", "Today"],
          ["/timetable/teachers", "My timetable"],
          ["/settings", "Settings"],
        ]
      : role === "student" || role === "parent"
        ? [
            ["/timetable/classes", "Class timetable"],
            ["/settings", "Settings"],
          ]
        : role === "super_admin"
          ? [["/schools", "Schools"], ...adminLinks]
          : adminLinks;

  useEffect(() => {
    if (role !== "super_admin") return;
    api.get<School[]>("/api/schools").then(setSchools).catch(() => setSchools([]));
  }, [role]);

  return (
    <div className="shell">
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="brand">
          <img src="/static/assets/sp-tech-logo.png" alt="SP-Tech Software Solution" className="brand-logo" />
          <span>Timetable</span>
        </div>
        {role === "super_admin" && (
          <label style={{ marginTop: 16, color: "#e7ded0" }}>
            Working school
            <select
              className="input"
              style={{ marginTop: 6 }}
              value={session?.school_id ?? ""}
              onChange={(e) => setActiveSchool(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">Select a school</option>
              {schools.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
        )}
        <nav className="side-nav">
          {links.map(([to, label]) => (
            <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "active" : "")} onClick={() => setOpen(false)}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="side-foot">
          {session?.full_name}
          <br />
          <span className="muted">{role?.replace("_", " ")}</span>
          <div style={{ marginTop: 10 }}>
            <button
              className="btn ghost"
              onClick={() => {
                logout();
                nav("/login");
              }}
            >
              Sign out
            </button>
          </div>
        </div>
      </aside>
      <main className="content">
        <button className="btn ghost mobile-toggle" onClick={() => setOpen(!open)}>
          Menu
        </button>
        <Outlet />
      </main>
    </div>
  );
}
