"use client";

import * as React from "react";
import { History, Bug } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import type { CommitEntry } from "@/lib/mock-data";
import { formatRelativeDate } from "@/lib/format";

export function HistorySheet({
  path,
  commits,
}: {
  path: string;
  commits: CommitEntry[];
}) {
  const [open, setOpen] = React.useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <History className="size-3.5" />
        View history
      </Button>
      <SheetContent side="right" className="w-full gap-0 sm:max-w-md">
        <SheetHeader>
          <SheetTitle className="font-mono text-sm">{path}</SheetTitle>
          <SheetDescription>Commit history from Git log analysis.</SheetDescription>
        </SheetHeader>
        <ol className="flex-1 overflow-auto px-4 pb-4">
          {commits.map((c, i) => (
            <li key={c.sha} className="relative flex gap-3 pb-6 last:pb-0">
              {i < commits.length - 1 && (
                <span
                  className="absolute left-[7px] top-4 h-full w-px bg-border"
                  aria-hidden="true"
                />
              )}
              <span
                className="relative mt-1.5 size-3.5 shrink-0 rounded-full border-2 border-background bg-primary"
                aria-hidden="true"
              />
              <div className="min-w-0">
                <p className="text-sm">{c.message}</p>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <span className="font-mono">{c.sha}</span>
                  <span>{c.author}</span>
                  <span>{formatRelativeDate(c.date)}</span>
                  {c.isBugFix && (
                    <Badge variant="outline" className="gap-1 border-risk-high/30 bg-risk-high/10 text-[10px] text-risk-high">
                      <Bug className="size-2.5" />
                      Bug fix
                    </Badge>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ol>
      </SheetContent>
    </Sheet>
  );
}
