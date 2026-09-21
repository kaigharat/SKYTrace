"use client";

import * as React from "react";
import { Code2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";

export function CodeSheet({
  path,
  code,
}: {
  path: string;
  code: string;
}) {
  const [open, setOpen] = React.useState(false);
  const lines = code.split("\n");

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <Code2 className="size-3.5" />
        View code
      </Button>
      <SheetContent side="right" className="w-full gap-0 sm:max-w-2xl">
        <SheetHeader>
          <SheetTitle className="font-mono text-sm">{path}</SheetTitle>
          <SheetDescription>Read-only preview from the last indexed commit.</SheetDescription>
        </SheetHeader>
        <div className="flex-1 overflow-auto px-4 pb-4">
          <pre className="rounded-lg border border-border bg-muted/30 p-4 text-xs leading-relaxed">
            <code className="font-mono">
              {lines.map((line, i) => (
                <div key={i} className="flex gap-4">
                  <span className="w-6 shrink-0 select-none text-right text-muted-foreground/50 tabular-nums">
                    {i + 1}
                  </span>
                  <span className="whitespace-pre-wrap break-all">{line || " "}</span>
                </div>
              ))}
            </code>
          </pre>
        </div>
      </SheetContent>
    </Sheet>
  );
}
