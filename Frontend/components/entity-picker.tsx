"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, ChevronsUpDown, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { searchApplicationOptions } from "@/lib/api/applications";
import { searchClientOptions } from "@/lib/api/clients";
import { searchJobOptions } from "@/lib/api/jobs";
import { searchVendorOptions, type EntityOption } from "@/lib/api/vendors";
import { cn } from "@/lib/utils";

type Searcher = (search: string, ids?: string[], status?: string) => Promise<EntityOption[]>;

const SEARCHERS: Record<"clients" | "vendors" | "jobs" | "applications", Searcher> = {
  clients: (search, ids) => searchClientOptions(search, ids),
  vendors: (search, ids) => searchVendorOptions(search, ids),
  jobs: async (search, ids, status) =>
    (await searchJobOptions(search, ids, status)).map((j) => ({
      id: j.id,
      name: `${j.title} · ${j.req_id}`,
    })),
  applications: async (search, ids, status) =>
    (await searchApplicationOptions(search, ids, status)).map((a) => ({
      id: a.id,
      name: `${a.candidate_name} — ${a.job_title}`,
    })),
};

interface EntityPickerProps {
  kind: keyof typeof SEARCHERS;
  /** The selected id, or null for none. */
  value: string | null | undefined;
  onChange: (value: string | null) => void;
  placeholder: string;
  /** An id never to offer, e.g. the client being edited as its own parent. */
  excludeId?: string;
  /** Only offer records in this status (jobs and applications). */
  status?: string;
}

/**
 * Type-to-search picker for clients, vendors, jobs and applications. For a "pick to add" control,
 * pass `value={null}` and act on each `onChange`.
 *
 * Replaces dropdowns that listed every record: at the tens of thousands a
 * Ceipal import brings in, those loaded the whole table into the browser and
 * froze the form. This asks the server for the first 20 matches instead.
 */
export function EntityPicker({
  kind,
  value,
  onChange,
  placeholder,
  excludeId,
  status,
}: EntityPickerProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search);
  const searcher = SEARCHERS[kind];

  const { data: matches, isFetching } = useQuery({
    queryKey: [kind, "options", debouncedSearch, status],
    queryFn: () => searcher(debouncedSearch, [], status),
    enabled: open,
    placeholderData: (previous) => previous,
  });

  // The selected record may not be among the current matches, so its name is
  // looked up by id to label the button.
  const { data: selected } = useQuery({
    queryKey: [kind, "options", "id", value],
    queryFn: () => searcher("", [value!]),
    enabled: Boolean(value),
    staleTime: 5 * 60 * 1000,
  });
  const selectedName = value ? selected?.[0]?.name : undefined;

  const options = (matches ?? []).filter((o) => o.id !== excludeId);

  function pick(id: string) {
    onChange(id);
    setOpen(false);
    setSearch("");
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <div className="flex items-center gap-1">
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-full justify-between font-normal"
          >
            <span className={cn("truncate", !selectedName && "text-muted-foreground")}>
              {selectedName ?? (value ? "Loading…" : placeholder)}
            </span>
            <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        {value && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-9 w-9 shrink-0"
            aria-label="Clear selection"
            onClick={() => onChange(null)}
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
      <PopoverContent className="w-[--radix-popover-trigger-width] min-w-[260px] p-0" align="start">
        {/* Filtering happens on the server; cmdk's own filter would re-filter
            the 20 results it was given and hide valid matches. */}
        <Command shouldFilter={false}>
          <CommandInput placeholder="Type to search…" value={search} onValueChange={setSearch} />
          <CommandList>
            <CommandEmpty>{isFetching ? "Searching…" : "No matches."}</CommandEmpty>
            {options.length > 0 && (
              <CommandGroup>
                {options.map((option) => (
                  <CommandItem key={option.id} value={option.id} onSelect={() => pick(option.id)}>
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        option.id === value ? "opacity-100" : "opacity-0",
                      )}
                    />
                    {option.name}
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
