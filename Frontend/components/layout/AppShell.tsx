"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useAuth } from "@/lib/auth/auth-context";
import {
  LayoutDashboard,
  Briefcase,
  FileText,
  Users,
  UserPlus,
  GitBranch,
  Calendar,
  FileSignature,
  Building2,
  Truck,
  BarChart3,
  Mail,
  Globe,
  Shield,
  Settings,
  Sparkles,
  Search,
  Bell,
  Plus,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const nav = [
  { section: "Overview", items: [{ to: "/", label: "Dashboard", icon: LayoutDashboard }] },
  {
    section: "Hiring",
    items: [
      { to: "/jobs", label: "Jobs", icon: Briefcase },
      { to: "/applications", label: "Applications", icon: FileText },
      { to: "/candidates", label: "Candidates", icon: Users },
      { to: "/talent-pool", label: "Talent Pool", icon: UserPlus },
      { to: "/pipeline", label: "Pipeline", icon: GitBranch },
      { to: "/interviews", label: "Interviews", icon: Calendar },
      { to: "/offers", label: "Offers", icon: FileSignature },
    ],
  },
  {
    section: "AI",
    items: [{ to: "/ai-review", label: "AI Review", icon: Sparkles }],
  },
  {
    section: "Business",
    items: [
      { to: "/clients", label: "Clients", icon: Building2 },
      { to: "/vendors", label: "Vendors", icon: Truck },
      { to: "/reports", label: "Reports", icon: BarChart3 },
      { to: "/templates", label: "Templates", icon: Mail },
    ],
  },
  {
    section: "System",
    items: [
      { to: "/careers", label: "Careers Portal", icon: Globe },
      { to: "/admin", label: "Admin", icon: Shield },
      { to: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

export function AppShell({
  children,
  title,
  breadcrumbs,
  actions,
}: {
  children?: ReactNode;
  title?: string;
  breadcrumbs?: { label: string; to?: string }[];
  actions?: ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isLoading, logout } = useAuth();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/auth/login");
    }
  }, [isLoading, user, router]);

  if (isLoading || !user) {
    return (
      <div className="min-h-screen grid place-items-center bg-background">
        <div className="text-sm text-muted-foreground">Loading…</div>
      </div>
    );
  }

  const initials = user.full_name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  const roleLabel =
    user.roles[0]?.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) ?? "Member";

  return (
    <div className="flex min-h-screen w-full bg-background">
      {/* Sidebar */}
      <aside className="hidden lg:flex w-64 flex-col bg-sidebar text-sidebar-foreground border-r border-sidebar-border sticky top-0 h-screen">
        <div className="h-14 flex items-center gap-2 px-5 border-b border-sidebar-border">
          <div className="h-8 w-8 rounded-md bg-sidebar-primary text-sidebar-primary-foreground grid place-items-center font-bold">
            A
          </div>
          <div>
            <div className="text-sm font-semibold leading-tight">ATS Tracker</div>
            <div className="text-[10px] uppercase tracking-wider text-sidebar-foreground/60">
              Recruiting OS
            </div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto py-3">
          {nav.map((sec) => (
            <div key={sec.section} className="px-3 mb-4">
              <div className="px-2 mb-1 text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/50">
                {sec.section}
              </div>
              <div className="space-y-0.5">
                {sec.items.map((it) => {
                  const active = it.to === "/" ? pathname === "/" : pathname.startsWith(it.to);
                  const Icon = it.icon;
                  return (
                    <Link
                      key={it.to}
                      href={it.to}
                      className={cn(
                        "flex items-center gap-2.5 px-2 py-1.5 rounded-md text-sm transition-colors",
                        active
                          ? "bg-sidebar-primary text-sidebar-primary-foreground"
                          : "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground text-sidebar-foreground/85",
                      )}
                    >
                      <Icon className="h-4 w-4" />
                      <span>{it.label}</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
        <div className="p-3 border-t border-sidebar-border">
          <div className="flex items-center gap-2 rounded-md p-2 bg-sidebar-accent/40">
            <Avatar className="h-8 w-8">
              <AvatarFallback className="bg-sidebar-primary text-sidebar-primary-foreground text-xs">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0">
              <div className="text-xs font-medium truncate">{user.full_name}</div>
              <div className="text-[10px] text-sidebar-foreground/60 truncate">{roleLabel}</div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 sticky top-0 z-20 bg-background/80 backdrop-blur border-b border-border flex items-center gap-3 px-4 lg:px-6">
          <div className="flex-1 max-w-md relative">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search candidates, jobs, req IDs…"
              className="pl-9 h-9 bg-muted/40 border-transparent focus-visible:bg-background"
            />
            <kbd className="hidden md:inline-flex absolute right-2 top-1/2 -translate-y-1/2 items-center gap-1 rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
              ⌘K
            </kbd>
          </div>
          <div className="flex items-center gap-2 ml-auto">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="sm" className="gap-1">
                  <Plus className="h-4 w-4" />
                  Quick Create
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuLabel>Create new</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/jobs/new">Job requisition</Link>
                </DropdownMenuItem>
                <DropdownMenuItem>Candidate</DropdownMenuItem>
                <DropdownMenuItem>Interview</DropdownMenuItem>
                <DropdownMenuItem>Note</DropdownMenuItem>
                <DropdownMenuItem>Email template</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-4 w-4" />
              <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-destructive" />
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="gap-2">
                  <Avatar className="h-6 w-6">
                    <AvatarFallback className="text-[10px]">{initials}</AvatarFallback>
                  </Avatar>
                  <span className="hidden md:inline text-xs">{roleLabel}</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>{user.full_name}</DropdownMenuLabel>
                <DropdownMenuItem disabled className="text-xs text-muted-foreground">
                  {user.email}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={logout}>Sign out</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {(title || breadcrumbs || actions) && (
          <div className="px-4 lg:px-8 pt-6 pb-2">
            {breadcrumbs && breadcrumbs.length > 0 && (
              <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
                {breadcrumbs.map((b, i) => (
                  <span key={i} className="flex items-center gap-1">
                    {b.to ? (
                      <Link href={b.to} className="hover:text-foreground">
                        {b.label}
                      </Link>
                    ) : (
                      <span>{b.label}</span>
                    )}
                    {i < breadcrumbs.length - 1 && <ChevronRight className="h-3 w-3" />}
                  </span>
                ))}
              </div>
            )}
            <div className="flex items-start justify-between gap-4 flex-wrap">
              {title && <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>}
              {actions && <div className="flex items-center gap-2">{actions}</div>}
            </div>
          </div>
        )}

        <main className="flex-1 px-4 lg:px-8 py-6">{children}</main>
      </div>
    </div>
  );
}

// Shared small components
export function StatCard({
  label,
  value,
  change,
  hint,
  tone = "default",
}: {
  label: string;
  value: string | number;
  change?: string;
  hint?: string;
  tone?: "default" | "success" | "warning" | "destructive";
}) {
  const toneCls = {
    default: "text-foreground",
    success: "text-[color:var(--color-success)]",
    warning: "text-[color:var(--color-warning-foreground)]",
    destructive: "text-destructive",
  }[tone];
  return (
    <div className="stat-card">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 flex items-baseline justify-between gap-2">
        <div className="text-2xl font-semibold tracking-tight">{value}</div>
        {change && (
          <Badge variant="secondary" className={cn("text-[10px]", toneCls)}>
            {change}
          </Badge>
        )}
      </div>
      {hint && <div className="mt-1 text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}

export function StageBadge({ stage }: { stage: string }) {
  const map: Record<string, string> = {
    Applied: "bg-slate-100 text-slate-700 border-slate-200",
    Screening: "bg-blue-50 text-blue-700 border-blue-200",
    Shortlisted: "bg-indigo-50 text-indigo-700 border-indigo-200",
    "Recruiter Interview": "bg-violet-50 text-violet-700 border-violet-200",
    "Technical Assessment": "bg-purple-50 text-purple-700 border-purple-200",
    "Hiring Manager Interview": "bg-fuchsia-50 text-fuchsia-700 border-fuchsia-200",
    "Panel Interview": "bg-pink-50 text-pink-700 border-pink-200",
    "Background Check": "bg-amber-50 text-amber-700 border-amber-200",
    Offer: "bg-orange-50 text-orange-700 border-orange-200",
    "Offer Accepted": "bg-emerald-50 text-emerald-700 border-emerald-200",
    Onboarding: "bg-teal-50 text-teal-700 border-teal-200",
    Hired: "bg-green-100 text-green-800 border-green-200",
    Rejected: "bg-red-50 text-red-700 border-red-200",
    "On Hold": "bg-yellow-50 text-yellow-700 border-yellow-200",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium",
        map[stage] || "bg-muted text-muted-foreground border-border",
      )}
    >
      {stage}
    </span>
  );
}

export function StatusDot({ status }: { status: string }) {
  const map: Record<string, string> = {
    Active: "bg-green-500",
    Draft: "bg-slate-400",
    "On Hold": "bg-yellow-500",
    Closed: "bg-slate-400",
    Cancelled: "bg-red-500",
  };
  return (
    <span className="inline-flex items-center gap-1.5 text-xs">
      <span className={cn("h-1.5 w-1.5 rounded-full", map[status] || "bg-slate-400")} />
      {status}
    </span>
  );
}

export function ScorePill({ score }: { score: number }) {
  const tone =
    score >= 80
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : score >= 60
        ? "bg-blue-50 text-blue-700 border-blue-200"
        : score >= 40
          ? "bg-amber-50 text-amber-700 border-amber-200"
          : "bg-red-50 text-red-700 border-red-200";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-semibold",
        tone,
      )}
    >
      <Sparkles className="h-3 w-3" />
      {score}
    </span>
  );
}
