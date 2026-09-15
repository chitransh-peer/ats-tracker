"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
import { forgotPassword } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Mail, Loader2, MailCheck } from "lucide-react";

export function ForgotPasswordClient() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [devToken, setDevToken] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => forgotPassword(email),
    onSuccess: (res) => {
      setSent(true);
      setDevToken(res.reset_token);
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : "Could not request a password reset."),
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

        {sent ? (
          <div className="space-y-4">
            <div className="text-center space-y-3">
              <MailCheck className="h-12 w-12 text-emerald-500 mx-auto" />
              <h1 className="text-xl font-semibold">Check your email</h1>
              <p className="text-sm text-muted-foreground">
                If an account exists for <span className="font-medium">{email}</span>, a reset link
                is on its way. The link expires in 30 minutes.
              </p>
            </div>

            {devToken && (
              <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-xs">
                <div className="font-semibold text-amber-900">
                  Development mode — no email was sent
                </div>
                <p className="mt-1 text-amber-800">
                  Use this token to reset the password directly:
                </p>
                <code className="mt-2 block break-all rounded bg-background border border-amber-200 px-2 py-1 font-mono">
                  {devToken}
                </code>
                <Button size="sm" className="mt-2 w-full" asChild>
                  <Link href={`/auth/reset-password?token=${encodeURIComponent(devToken)}`}>
                    Continue to reset password
                  </Link>
                </Button>
              </div>
            )}

            <div className="text-center">
              <Link href="/auth/login" className="text-xs text-primary hover:underline">
                Back to sign in
              </Link>
            </div>
          </div>
        ) : (
          <>
            <h1 className="text-2xl font-semibold tracking-tight">Reset your password</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Enter your work email and we&apos;ll send you a reset link.
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
              <Button type="submit" className="w-full" disabled={mutation.isPending || !email}>
                {mutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                    Sending…
                  </>
                ) : (
                  "Send reset link"
                )}
              </Button>
            </form>
            <p className="mt-6 text-xs text-muted-foreground">
              Remembered it?{" "}
              <Link href="/auth/login" className="text-primary hover:underline">
                Sign in
              </Link>
            </p>
          </>
        )}
      </div>
    </main>
  );
}
