"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { resetPassword } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Lock, KeyRound, Loader2, CheckCircle2 } from "lucide-react";

export function ResetPasswordClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [token, setToken] = useState(searchParams.get("token") ?? "");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const mismatch = confirm.length > 0 && password !== confirm;

  const mutation = useMutation({
    mutationFn: () => resetPassword(token, password),
    onSuccess: () => {
      setDone(true);
      setTimeout(() => router.push("/auth/login"), 1800);
    },
    onError: (err) =>
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not reset your password. The link may have expired.",
      ),
  });

  return (
    <main className="min-h-screen grid place-items-center bg-background px-6 py-12">
      <div className="w-full max-w-sm">
        <Link href="/" className="flex items-center gap-2 mb-10">
          <div className="h-9 w-9 rounded-md bg-primary text-primary-foreground grid place-items-center font-bold">
            P
          </div>
          <div>
            <div className="text-sm font-semibold leading-tight">
              Peer Consulting Resources Inc.
            </div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Recruiting OS
            </div>
          </div>
        </Link>

        {done ? (
          <div className="text-center space-y-3">
            <CheckCircle2 className="h-12 w-12 text-emerald-500 mx-auto" />
            <h1 className="text-xl font-semibold">Password updated</h1>
            <p className="text-sm text-muted-foreground">Redirecting you to sign in…</p>
          </div>
        ) : (
          <>
            <h1 className="text-2xl font-semibold tracking-tight">Choose a new password</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Reset links expire 30 minutes after they&apos;re issued.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                setError(null);
                mutation.mutate();
              }}
              className="mt-8 space-y-4"
            >
              {error && (
                <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {error}
                </div>
              )}
              <div>
                <Label htmlFor="token">Reset token</Label>
                <div className="relative mt-1.5">
                  <KeyRound className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="token"
                    required
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    className="pl-9 font-mono text-xs"
                  />
                </div>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Filled in automatically when you arrive from the reset link.
                </p>
              </div>
              <div>
                <Label htmlFor="password">New password</Label>
                <div className="relative mt-1.5">
                  <Lock className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="password"
                    type="password"
                    required
                    minLength={12}
                    autoComplete="new-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-9"
                  />
                </div>
                <p className="mt-1 text-[11px] text-muted-foreground">At least 12 characters.</p>
              </div>
              <div>
                <Label htmlFor="confirm">Confirm new password</Label>
                <div className="relative mt-1.5">
                  <Lock className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="confirm"
                    type="password"
                    required
                    autoComplete="new-password"
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    className="pl-9"
                  />
                </div>
                {mismatch && (
                  <p className="mt-1 text-[11px] text-destructive">Passwords don&apos;t match.</p>
                )}
              </div>
              <Button
                type="submit"
                className="w-full"
                disabled={mutation.isPending || !token || password.length < 12 || mismatch}
              >
                {mutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                    Updating…
                  </>
                ) : (
                  "Update password"
                )}
              </Button>
            </form>
            <p className="mt-6 text-xs text-muted-foreground">
              Need a new link?{" "}
              <Link href="/auth/forgot-password" className="text-primary hover:underline">
                Request one
              </Link>
            </p>
          </>
        )}
      </div>
    </main>
  );
}
