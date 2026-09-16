"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Lock, Loader2, CheckCircle2 } from "lucide-react";
import { changePassword } from "@/lib/api/auth";
import { ApiError, setTokens } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";

const MIN_LENGTH = 12;

export function ChangePasswordClient() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { user, isLoading } = useAuth();
  const router = useRouter();

  const forced = user?.must_change_password ?? false;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    // Checked here as well as by the API so the mismatch is caught without a
    // round trip; the length rule is enforced server-side regardless.
    if (newPassword !== confirmPassword) {
      setError("Those two passwords don't match.");
      return;
    }
    if (newPassword.length < MIN_LENGTH) {
      setError(`Your new password must be at least ${MIN_LENGTH} characters.`);
      return;
    }

    setLoading(true);
    try {
      const tokens = await changePassword(currentPassword, newPassword);
      // Changing the password revokes every existing token, so the pair that
      // comes back is the only one that still works. Store it before navigating
      // or the very next request would 401.
      setTokens(tokens.access_token, tokens.refresh_token);
      // A full load rather than router.push: the cached user profile still says
      // must_change_password, and this is the one moment where throwing all
      // client state away is cheaper than reconciling it.
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen grid place-items-center bg-background px-6 py-12">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2 mb-8">
          <div className="h-9 w-9 rounded-md bg-primary text-primary-foreground grid place-items-center font-bold">
            A
          </div>
          <div>
            <div className="text-sm font-semibold leading-tight">ATS Tracker</div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Recruiting OS
            </div>
          </div>
        </div>

        <h1 className="text-2xl font-semibold tracking-tight">
          {forced ? "Choose your password" : "Change your password"}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {forced
            ? "You signed in with a temporary password. Pick one of your own to continue."
            : "Pick a new password for your account."}
        </p>

        {!isLoading && user && (
          <p className="mt-3 text-xs text-muted-foreground">
            Signed in as <span className="font-medium text-foreground">{user.email}</span>
          </p>
        )}

        <form onSubmit={onSubmit} className="mt-8 space-y-4">
          {error && (
            <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}

          <div>
            <Label htmlFor="current-password">
              {forced ? "Temporary password" : "Current password"}
            </Label>
            <div className="relative mt-1.5">
              <Lock className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="current-password"
                type="password"
                autoComplete="current-password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="pl-9"
              />
            </div>
            {forced && (
              <p className="mt-1.5 text-xs text-muted-foreground">
                The one from your invitation email.
              </p>
            )}
          </div>

          <div>
            <Label htmlFor="new-password">New password</Label>
            <div className="relative mt-1.5">
              <Lock className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="new-password"
                type="password"
                autoComplete="new-password"
                required
                minLength={MIN_LENGTH}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="pl-9"
              />
            </div>
            <p className="mt-1.5 text-xs text-muted-foreground">
              At least {MIN_LENGTH} characters.
            </p>
          </div>

          <div>
            <Label htmlFor="confirm-password">Confirm new password</Label>
            <div className="relative mt-1.5">
              <Lock className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="confirm-password"
                type="password"
                autoComplete="new-password"
                required
                minLength={MIN_LENGTH}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                Saving…
              </>
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4 mr-1" />
                Set password and continue
              </>
            )}
          </Button>
        </form>
      </div>
    </main>
  );
}
