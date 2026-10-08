"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Briefcase, Building2, Loader2, Search, Truck, User } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { globalSearch, type SearchResults } from "@/lib/api/search";
import { cn } from "@/lib/utils";

type Hit = { key: string; href: string; label: string; detail?: string; exact?: boolean };
type Group = { title: string; icon: typeof Search; hits: Hit[] };

function groupsOf(data: SearchResults): Group[] {
  const q = data.query.toLowerCase();
  return [
    {
      title: "Jobs",
      icon: Briefcase,
      hits: data.jobs.map((j) => ({
        key: `job-${j.id}`,
        href: `/jobs/${j.id}`,
        label: j.title,
        detail: `${j.req_id} · ${j.status}`,
        exact: j.req_id.toLowerCase() === q,
      })),
    },
    {
      title: "Candidates",
      icon: User,
      hits: data.candidates.map((c) => ({
        key: `candidate-${c.id}`,
        href: `/candidates/${c.id}`,
        label: c.full_name,
        detail: [c.current_title, c.email].filter(Boolean).join(" · ") || undefined,
        exact: (c.email ?? "").toLowerCase() === q,
      })),
    },
    {
      title: "Clients",
      icon: Building2,
      hits: data.clients.map((c) => ({
        key: `client-${c.id}`,
        href: `/clients/${c.id}`,
        label: c.name,
      })),
    },
    {
      title: "Vendors",
      icon: Truck,
      hits: data.vendors.map((v) => ({
        key: `vendor-${v.id}`,
        href: `/vendors/${v.id}`,
        label: v.name,
      })),
    },
  ].filter((g) => g.hits.length > 0);
}

/**
 * The header search box. Results drop down as you type; Enter opens the
 * highlighted result, or goes straight to an exact req-ID / email match or a
 * lone result, and always shows something — results or "No results".
 */
export function GlobalSearch() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const [text, setText] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  // Enter searches at once instead of waiting out the debounce, and opens
  // the match once results arrive.
  const [submitted, setSubmitted] = useState<string | null>(null);
  const debounced = useDebouncedValue(text.trim());
  const term = submitted ?? debounced;

  const { data, isFetching, isError } = useQuery({
    queryKey: ["global-search", term],
    queryFn: () => globalSearch(term),
    enabled: term.length > 0,
    staleTime: 30_000,
  });

  const groups = useMemo(() => (data && data.query === term ? groupsOf(data) : []), [data, term]);
  const hits = groups.flatMap((g) => g.hits);
  const settled = Boolean(data && data.query === term) && !isFetching;

  function go(hit: Hit) {
    setOpen(false);
    setSubmitted(null);
    setText("");
    inputRef.current?.blur();
    router.push(hit.href);
  }

  // After Enter: jump to an exact match or the only result once they're in.
  useEffect(() => {
    if (submitted === null || !settled) return;
    const target = hits.find((h) => h.exact) ?? (hits.length === 1 ? hits[0] : undefined);
    if (target) go(target);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [submitted, settled]);

  // ⌘K / Ctrl+K focuses the box, as the hint in it promises.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
        setOpen(true);
      }
    }
    function onPointer(e: PointerEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, []);

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActive((i) => (hits.length ? (i + 1) % hits.length : -1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => (hits.length ? (i <= 0 ? hits.length - 1 : i - 1) : -1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (active >= 0 && hits[active]) {
        go(hits[active]);
        return;
      }
      const q = text.trim();
      if (!q) return;
      setOpen(true);
      setSubmitted(q);
    } else if (e.key === "Escape") {
      setOpen(false);
      inputRef.current?.blur();
    }
  }

  const showPanel = open && text.trim().length > 0;
  const loading = term.length > 0 && !settled && !isError;
  let index = -1;

  return (
    <div ref={boxRef} className="flex-1 max-w-md relative">
      <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
      <Input
        ref={inputRef}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          setSubmitted(null);
          setActive(-1);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        placeholder="Search candidates, jobs, req IDs…"
        aria-label="Search"
        role="combobox"
        aria-expanded={showPanel}
        aria-controls="global-search-results"
        className="pl-9 h-9 bg-muted/40 border-transparent focus-visible:bg-background"
      />
      <kbd className="hidden md:inline-flex absolute right-2 top-1/2 -translate-y-1/2 items-center gap-1 rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
        ⌘K
      </kbd>
      {showPanel && (
        <div
          id="global-search-results"
          role="listbox"
          className="absolute left-0 right-0 top-full mt-1 z-50 max-h-[70vh] overflow-y-auto rounded-md border bg-popover text-popover-foreground shadow-lg"
        >
          {isError ? (
            <div className="p-3 text-sm text-destructive">Search failed. Try again.</div>
          ) : loading && hits.length === 0 ? (
            <div className="flex items-center gap-2 p-3 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Searching…
            </div>
          ) : hits.length === 0 ? (
            <div className="p-3 text-sm text-muted-foreground">
              No results for &ldquo;{text.trim()}&rdquo;
            </div>
          ) : (
            groups.map((g) => {
              const Icon = g.icon;
              return (
                <div key={g.title} className="py-1">
                  <div className="px-3 pt-1 pb-0.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    {g.title}
                  </div>
                  {g.hits.map((hit) => {
                    index += 1;
                    const i = index;
                    return (
                      <button
                        key={hit.key}
                        type="button"
                        role="option"
                        aria-selected={i === active}
                        onMouseEnter={() => setActive(i)}
                        onClick={() => go(hit)}
                        className={cn(
                          "flex w-full items-start gap-2 px-3 py-1.5 text-left text-sm",
                          i === active ? "bg-accent text-accent-foreground" : "hover:bg-muted/60",
                        )}
                      >
                        <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                        <span className="min-w-0">
                          <span className="block truncate">{hit.label}</span>
                          {hit.detail && (
                            <span className="block truncate text-xs text-muted-foreground">
                              {hit.detail}
                            </span>
                          )}
                        </span>
                      </button>
                    );
                  })}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
