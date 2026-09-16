"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Mail, Lock, Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth/auth-context";
import { ApiError } from "@/lib/api/client";

export function LoginClient() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login } = useAuth();
  const router = useRouter();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const mustChangePassword = await login(email, password);
      // An invited account cannot use anything else until it has its own
      // password, so go straight there rather than bouncing off the dashboard.
      router.push(mustChangePassword ? "/auth/change-password" : "/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen grid lg:grid-cols-2 bg-background">
      <div className="flex flex-col justify-center px-6 sm:px-12 lg:px-20 py-12">
        <Link href="/" className="flex items-center gap-2 mb-10">
          <div className="h-9 w-9 rounded-md bg-primary text-primary-foreground grid place-items-center font-bold">
            A
          </div>
          <div>
            <div className="text-sm font-semibold leading-tight">ATS Tracker</div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Recruiting OS
            </div>
          </div>
        </Link>

        <div className="max-w-sm w-full">
          <h1 className="text-2xl font-semibold tracking-tight">Welcome back</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Sign in to your recruiting workspace.
          </p>

          <form onSubmit={onSubmit} className="mt-8 space-y-4">
            {error && (
              <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            )}
            <div>
              <Label htmlFor="email">Work email</Label>
              <div className="relative mt-1.5">
                <Mail className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <Link href="/auth/forgot-password" className="text-xs text-primary hover:underline">
                  Forgot password?
                </Link>
              </div>
              <div className="relative mt-1.5">
                <Lock className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  Signing in…
                </>
              ) : (
                "Sign in"
              )}
            </Button>
          </form>

          <p className="mt-8 text-xs text-muted-foreground">
            By signing in you agree to our Terms of Service and Privacy Policy.
          </p>
        </div>
      </div>

      <aside className="hidden lg:flex bg-sidebar text-sidebar-foreground p-12 flex-col justify-between">
        <div className="text-xs uppercase tracking-wider text-sidebar-foreground/60">
          Recruiting Operations Platform
        </div>
        <div className="space-y-6">
          <h2 className="text-3xl font-semibold leading-tight max-w-md">
            Ship every hire faster with pipelines, AI matching, and analytics in one place.
          </h2>
          <div className="grid grid-cols-3 gap-4 max-w-md">
            {[
              { k: "38%", v: "Faster time-to-fill" },
              { k: "2.4×", v: "More shortlists" },
              { k: "96%", v: "Recruiter adoption" },
            ].map((s) => (
              <Card
                key={s.k}
                className="bg-sidebar-accent/30 border-sidebar-border text-sidebar-foreground"
              >
                <CardContent className="p-4">
                  <div className="text-2xl font-semibold">{s.k}</div>
                  <div className="text-[11px] text-sidebar-foreground/70 mt-0.5">{s.v}</div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
        <div className="text-xs text-sidebar-foreground/60">
          © {new Date().getFullYear()} ATS Tracker
        </div>
      </aside>
    </main>
  );
}
