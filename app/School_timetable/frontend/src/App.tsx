import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Setup from "./pages/Setup";
import Classes from "./pages/Classes";
import Sections from "./pages/Sections";
import Subjects from "./pages/Subjects";
import Teachers from "./pages/Teachers";
import Rooms from "./pages/Rooms";
import Periods from "./pages/Periods";
import Rules from "./pages/Rules";
import Generate from "./pages/Generate";
import TimetableView from "./pages/TimetableView";
import Editor from "./pages/Editor";
import AiAssistant from "./pages/AiAssistant";
import ImportPage from "./pages/Import";
import Settings from "./pages/Settings";
import TeacherHome from "./pages/TeacherHome";
import Schools from "./pages/Schools";
import Accounts from "./pages/Accounts";

function homeFor(role: string | null) {
  if (role === "teacher") return "/teacher";
  if (role === "super_admin") return "/schools";
  return "/dashboard";
}

function Guard({ children }: { children: ReactNode }) {
  const { session } = useAuth();
  if (!session) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function SuperOnly({ children }: { children: ReactNode }) {
  const { role } = useAuth();
  if (role !== "super_admin") return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

function SchoolAdminOnly({ children }: { children: ReactNode }) {
  const { role } = useAuth();
  if (role !== "school_admin" && role !== "super_admin") return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export default function App() {
  const { session } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={session ? <Navigate to={homeFor(session.role)} replace /> : <Login />} />
      <Route path="/register" element={<Navigate to="/login" replace />} />
      <Route
        element={
          <Guard>
            <Layout />
          </Guard>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route
          path="/schools"
          element={
            <SuperOnly>
              <Schools />
            </SuperOnly>
          }
        />
        <Route
          path="/accounts"
          element={
            <SchoolAdminOnly>
              <Accounts />
            </SchoolAdminOnly>
          }
        />
        <Route path="/setup" element={<Setup />} />
        <Route path="/classes" element={<Classes />} />
        <Route path="/sections" element={<Sections />} />
        <Route path="/subjects" element={<Subjects />} />
        <Route path="/teachers" element={<Teachers />} />
        <Route path="/rooms" element={<Rooms />} />
        <Route path="/periods" element={<Periods />} />
        <Route path="/rules" element={<Rules />} />
        <Route path="/timetable/generate" element={<Generate />} />
        <Route path="/timetable/master" element={<TimetableView kind="master" />} />
        <Route path="/timetable/classes" element={<TimetableView kind="class" />} />
        <Route path="/timetable/teachers" element={<TimetableView kind="teacher" />} />
        <Route path="/timetable/rooms" element={<TimetableView kind="room" />} />
        <Route path="/timetable/editor" element={<Editor />} />
        <Route path="/ai-assistant" element={<AiAssistant />} />
        <Route path="/import" element={<ImportPage />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/teacher" element={<TeacherHome />} />
      </Route>
      <Route path="*" element={<Navigate to={session ? homeFor(session.role) : "/login"} replace />} />
    </Routes>
  );
}
