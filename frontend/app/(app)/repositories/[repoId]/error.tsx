"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function RepositoryDashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-3 py-16 text-center">
      <Card className="w-full items-center gap-3 p-8">
        <AlertTriangle className="size-8 text-risk-high" aria-hidden="true" />
        <h1 className="text-lg font-semibold">Couldn&apos;t load this repository</h1>
        <p className="text-sm text-muted-foreground">
          Something went wrong while loading the dashboard. This has been logged.
        </p>
        <div className="mt-2 flex gap-2">
          <Button variant="outline" asChild>
            <Link href="/repositories">All repositories</Link>
          </Button>
          <Button onClick={reset}>
            <RotateCcw className="size-4" />
            Try again
          </Button>
        </div>
      </Card>
    </div>
  );
}
