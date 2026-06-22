"use client";
import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { api, setToken } from "@/lib/api";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/";
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setErr(null);
    try {
      const r = await api.login(email, pw);
      setToken(r.access_token);
      router.push(next);
    } catch (e: any) {
      setErr(e.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-sm mx-auto px-4 py-16">
      <h1 className="text-2xl font-semibold mb-6">Sign in</h1>
      <form onSubmit={submit} className="card p-5 space-y-3">
        <input
          className="input"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="input"
          type="password"
          autoComplete="current-password"
          placeholder="Password"
          required
          minLength={8}
          value={pw}
          onChange={(e) => setPw(e.target.value)}
        />
        {err && <div className="text-danger text-sm">{err}</div>}
        <button className="btn-primary w-full justify-center" disabled={loading}>
          {loading && <Loader2 size={16} className="animate-spin" />} Sign in
        </button>
        <div className="text-center text-sm text-text-muted">
          No account?{" "}
          <Link href="/register" className="text-accent underline">
            Create one
          </Link>
        </div>
      </form>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
