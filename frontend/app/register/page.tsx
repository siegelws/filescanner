"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { api, setToken } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (pw.length < 8) {
      setErr("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    setErr(null);
    try {
      const r = await api.register(email, pw);
      setToken(r.access_token);
      router.push("/");
    } catch (e: any) {
      setErr(e.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-sm mx-auto px-4 py-16">
      <h1 className="text-2xl font-semibold mb-6">Create account</h1>
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
          autoComplete="new-password"
          placeholder="Password (min 8 chars)"
          required
          minLength={8}
          value={pw}
          onChange={(e) => setPw(e.target.value)}
        />
        {err && <div className="text-danger text-sm">{err}</div>}
        <button className="btn-primary w-full justify-center" disabled={loading}>
          {loading && <Loader2 size={16} className="animate-spin" />} Create account
        </button>
        <div className="text-center text-sm text-text-muted">
          Already have one?{" "}
          <Link href="/login" className="text-accent underline">
            Sign in
          </Link>
        </div>
      </form>
    </div>
  );
}
