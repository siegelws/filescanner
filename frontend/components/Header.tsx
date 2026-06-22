"use client";
import Link from "next/link";
import { ShieldCheck, History, LogIn, LogOut, UserPlus, Sparkles } from "lucide-react";
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
    <header className="border-b border-border bg-white/70 backdrop-blur-lg sticky top-0 z-30 shadow-soft">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-full bg-gold-gradient flex items-center justify-center shadow-gold">
            <ShieldCheck className="text-white" size={20} />
          </div>
          <div className="leading-tight">
            <div className="font-display text-xl font-semibold text-lux">FileScan</div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-text-subtle font-medium">
              multi-engine analysis
            </div>
          </div>
        </Link>
        <nav className="flex items-center gap-2">
          {user ? (
            <>
              <Link href="/history" className="btn">
                <History size={16} /> History
              </Link>
              <span className="text-text-muted text-sm hidden sm:inline-flex items-center gap-1.5">
                <Sparkles size={13} className="text-accent" />
                {user.email}
              </span>
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
