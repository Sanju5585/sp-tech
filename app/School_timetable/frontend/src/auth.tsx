import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api, getSession, setSession } from "./api";
import type { Role, Session } from "./types";

type AuthCtx = {
  session: Session | null;
  login: (email: string, password: string) => Promise<Session>;
  loginWithSso: (token: string) => Promise<Session>;
  logout: () => void;
  setActiveSchool: (schoolId: number | null) => void;
  role: Role | null;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, set] = useState<Session | null>(getSession());
  const ssoTried = useRef(false);
  const value = useMemo<AuthCtx>(
    () => ({
      session,
      role: session?.role ?? null,
      async login(email, password) {
        const s = await api.post<Session>("/api/auth/login", {
          email: email.trim(),
          password: password.trim(),
        });
        setSession(s);
        set(s);
        return s;
      },
      async loginWithSso(token) {
        const s = await api.post<Session>("/api/auth/portal-sso", { token });
        setSession(s);
        set(s);
        return s;
      },
      setActiveSchool(schoolId) {
        const current = getSession();
        if (!current) return;
        const next = { ...current, school_id: schoolId };
        setSession(next);
        set(next);
      },
      logout() {
        setSession(null);
        set(null);
      },
    }),
    [session]
  );

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("sso");
    if (!token || ssoTried.current) return;
    ssoTried.current = true;
    value
      .loginWithSso(token)
      .then(() => {
        const url = new URL(window.location.href);
        url.searchParams.delete("sso");
        window.history.replaceState({}, "", url.pathname + url.search);
      })
      .catch(() => undefined);
  }, [value]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("auth");
  return ctx;
}
