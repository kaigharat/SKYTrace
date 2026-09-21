"use client";

import * as React from "react";
import { use } from "react";
import Link from "next/link";
import { CheckCircle2, CircleDashed, Loader2, PartyPopper } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  analysisJobs,
  getRepository,
  repositoryHealth,
} from "@/lib/mock-data";
import type { AnalysisStep } from "@/lib/types";
import { cn } from "@/lib/utils";

const FRESH_STEPS: AnalysisStep[] = [
  { key: "clone", label: "Cloning repository" },
  { key: "parse", label: "Parsing source (Tree-sitter + AST)" },
  { key: "graph", label: "Building dependency & call graph" },
  { key: "history", label: "Analyzing Git history" },
  { key: "models", label: "Running risk models" },
  { key: "index", label: "Indexing historical embeddings" },
  { key: "finalize", label: "Computing repository health score" },
].map((s) => ({ ...s, status: "pending" as const }));

export default function AnalyzingPage({
  params,
}: {
  params: Promise<{ repoId: string }>;
}) {
  const { repoId } = use(params);
  const repo = getRepository(repoId);
  const liveJob = analysisJobs[repoId];
  const hasDashboard = Boolean(repositoryHealth[repoId]);

  const [steps, setSteps] = React.useState<AnalysisStep[]>(() =>
    liveJob ? liveJob.steps : FRESH_STEPS,
  );
  const [animating] = React.useState(!liveJob);

  React.useEffect(() => {
    if (liveJob) return; // static live-poll snapshot, not animated
    let cancelled = false;
    let index = 0;

    function tick() {
      if (cancelled) return;
      setSteps((prev) => {
        const next = prev.map((s, i) => {
          if (i < index) return { ...s, status: "done" as const };
          if (i === index) return { ...s, status: "active" as const };
          return { ...s, status: "pending" as const };
        });
        return next;
      });
      index += 1;
      if (index <= FRESH_STEPS.length) {
        window.setTimeout(tick, 850);
      } else {
        setSteps((prev) => prev.map((s) => ({ ...s, status: "done" as const })));
      }
    }

    const start = window.setTimeout(tick, 400);
    return () => {
      cancelled = true;
      window.clearTimeout(start);
    };
  }, [liveJob]);

  const doneCount = steps.filter((s) => s.status === "done").length;
  const progress = liveJob ? liveJob.progress : Math.round((doneCount / steps.length) * 100);
  const complete = !liveJob && doneCount === steps.length;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Analyzing {repo?.fullName ?? repoId}
        </h1>
        <p className="text-sm text-muted-foreground">
          {liveJob
            ? "Ingestion pipeline is running. This view reflects the latest known status."
            : "Repository Intelligence AI is building a unified representation of this repository."}
        </p>
      </div>

      <Card className="gap-5 p-6">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Overall progress</span>
          <span className="font-mono text-sm tabular-nums text-muted-foreground">
            {progress}%
          </span>
        </div>
        <Progress value={progress} aria-label="Analysis progress" />

        <ul
          className="flex flex-col gap-3"
          aria-live="polite"
          aria-atomic="false"
        >
          {steps.map((step) => (
            <li key={step.key} className="flex items-start gap-3">
              {step.status === "done" && (
                <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-risk-low" aria-hidden="true" />
              )}
              {step.status === "active" && (
                <Loader2 className="mt-0.5 size-4 shrink-0 animate-spin text-primary" aria-hidden="true" />
              )}
              {step.status === "pending" && (
                <CircleDashed className="mt-0.5 size-4 shrink-0 text-muted-foreground/50" aria-hidden="true" />
              )}
              <div className="min-w-0">
                <p
                  className={cn(
                    "text-sm",
                    step.status === "pending" ? "text-muted-foreground" : "text-foreground",
                    step.status === "active" && "font-medium",
                  )}
                >
                  {step.label}
                  {step.status === "done" && (
                    <span className="ml-2 text-xs font-normal text-muted-foreground">Done</span>
                  )}
                  {step.status === "active" && (
                    <span className="ml-2 text-xs font-normal text-primary">In progress…</span>
                  )}
                </p>
                {step.detail && (
                  <p className="text-xs text-muted-foreground">{step.detail}</p>
                )}
              </div>
            </li>
          ))}
        </ul>
      </Card>

      {complete && (
        <Card className="items-center gap-3 p-6 text-center">
          <PartyPopper className="size-6 text-risk-low" aria-hidden="true" />
          <p className="text-sm font-medium">Analysis complete</p>
          {hasDashboard ? (
            <>
              <p className="text-xs text-muted-foreground">
                The repository dashboard, risk findings and graph are ready.
              </p>
              <Button asChild className="mt-1">
                <Link href={`/repositories/${repoId}`}>Open repository dashboard</Link>
              </Button>
            </>
          ) : (
            <>
              <p className="max-w-sm text-xs text-muted-foreground">
                This sample repository isn&apos;t wired to demo data yet. Explore the fully
                analyzed demo repository instead.
              </p>
              <Button asChild className="mt-1">
                <Link href="/repositories/repo-orbit-payments">Open demo dashboard</Link>
              </Button>
            </>
          )}
        </Card>
      )}

      {!complete && !liveJob && animating && (
        <p className="text-center text-xs text-muted-foreground">
          This usually takes 3–8 minutes for repositories under 500 files.
        </p>
      )}
    </div>
  );
}
