"use client";
import Link from "next/link";
import { ShieldCheck, History, LogIn, LogOut, UserPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { api, getToken, setToken } from "@/lib/api";

export function Header() {
  const [user, setUser] = useState<{ email: string } | null>(null);

  useEffect(() => {
    if (!getToken()) return;
    api.me().then((u) => u && setUser(u)).catch(() => {});
  }, []);

  function logout() {
    setToken(null);
    setUser(null);
    window.location.href = "/";
  }

  return (
    <header className="border-b border-border bg-bg-subtle/80 backdrop-blur sticky top-0 z-30">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <ShieldCheck className="text-accent" size={22} />
          <span>FileScan</span>
          <span className="text-text-subtle text-xs font-mono">multi-av</span>
        </Link>
        <nav className="flex items-center gap-2">
          {user ? (
            <>
              <Link href="/history" className="btn">
                <History size={16} /> History
              </Link>
              <span className="text-text-muted text-sm hidden sm:block">{user.email}</span>
              <button onClick={logout} className="btn">
                <LogOut size={16} /> Sign out
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="btn">
                <LogIn size={16} /> Sign in
              </Link>
              <Link href="/register" className="btn-primary">
                <UserPlus size={16} /> Sign up
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
