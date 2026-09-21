"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Check, ChevronsUpDown, Plus } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import type { Repository } from "@/lib/types";
import { cn } from "@/lib/utils";

export function RepoSwitcher({
  repositories,
  activeRepoId,
}: {
  repositories: Repository[];
  activeRepoId?: string;
}) {
  const router = useRouter();
  const active = repositories.find((r) => r.id === activeRepoId);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className="w-full justify-between gap-2 border-sidebar-border bg-sidebar-accent/40 px-3 text-left hover:bg-sidebar-accent"
        >
          <span className="flex min-w-0 flex-col items-start">
            <span className="w-full truncate text-xs font-medium text-sidebar-foreground">
              {active ? active.fullName : "Select repository"}
            </span>
            {active && (
              <span className="text-[11px] text-muted-foreground">
                {active.analysisStatus === "completed" ? "Analyzed" : "Analyzing…"}
              </span>
            )}
          </span>
          <ChevronsUpDown className="size-3.5 shrink-0 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-72">
        <DropdownMenuLabel>Connected repositories</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {repositories.map((repo) => (
          <DropdownMenuItem
            key={repo.id}
            onClick={() => router.push(`/repositories/${repo.id}`)}
            className="flex items-center justify-between gap-2"
          >
            <span className="flex min-w-0 flex-col">
              <span className="truncate text-sm">{repo.fullName}</span>
              <span className="text-[11px] text-muted-foreground">
                {repo.analysisStatus === "completed"
                  ? `${repo.languages.join(", ")}`
                  : "Analysis in progress"}
              </span>
            </span>
            {repo.id === activeRepoId && <Check className="size-4 shrink-0 text-primary" />}
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/onboarding" className={cn("flex items-center gap-2 text-primary")}>
            <Plus className="size-4" />
            Connect a repository
          </Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
