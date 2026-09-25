"use client";

import * as React from "react";
import { use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  CircleDashed,
  ExternalLink,
  Loader2,
  PartyPopper,
  RefreshCw,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { AnalysisJob, AnalysisStep, Repository } from "@/lib/types";
import { cn } from "@/lib/utils";

const DEFAULT_STEPS: AnalysisStep[] = [
  { key: "clone", label: "Fetching repository from GitHub", status: "pending" },
  { key: "parse", label: "Parsing source files & syntax trees", status: "pending" },
  { key: "graph", label: "Building dependency & import graph", status: "pending" },
  { key: "history", label: "Analyzing Git history & pull requests", status: "pending" },
  { key: "models", label: "Running ML risk models on source files", status: "pending" },
  { key: "index", label: "Indexing historical embeddings", status: "pending" },
  { key: "finalize", label: "Computing repository health score", status: "pending" },
];

export default function AnalyzingPage({
  params,
}: {
  params: Promise<{ repoId: string }>;
}) {
  const router = useRouter();
  const { repoId } = use(params);

  const [repo, setRepo] = React.useState<Repository | null>(null);
  const [job, setJob] = React.useState<AnalysisJob | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [retrying, setRetrying] = React.useState(false);
  const [redirecting, setRedirecting] = React.useState(false);

  // Poll analysis status
  const pollStatus = React.useCallback(async () => {
    try {
      const [fetchedRepo, fetchedJob] = await Promise.all([
        api.getRepository(repoId).catch(() => null),
        api.getAnalysisStatus(repoId).catch(() => null),
      ]);

      if (fetchedRepo) {
        setRepo(fetchedRepo);
      }

      if (fetchedJob) {
        setJob(fetchedJob);

        if (fetchedJob.status === "completed" || fetchedRepo?.analysisStatus === "completed") {
          // Success! Redirect after a short delay
          setRedirecting(true);
          setTimeout(() => {
            router.push(`/repositories/${repoId}`);
          }, 1800);
          return true; // Stop polling
        }

        if (fetchedJob.status === "failed") {
          setError(fetchedJob.errorMessage || "Analysis failed. Please check repository access and retry.");
          return true; // Stop polling
        }
      }
      return false;
    } catch (err: unknown) {
      console.error("Polling error:", err);
      return false;
    }
  }, [repoId, router]);

  React.useEffect(() => {
    let cancelled = false;
    let timerId: NodeJS.Timeout;

    async function runPoll() {
      if (cancelled) return;
      const shouldStop = await pollStatus();
      if (!shouldStop && !cancelled) {
        timerId = setTimeout(runPoll, 2000);
      }
    }

    runPoll();

    return () => {
      cancelled = true;
      if (timerId) clearTimeout(timerId);
    };
  }, [pollStatus]);

  async function handleRetry() {
    setRetrying(true);
    setError(null);
    try {
      await api.analyzeRepository(repoId);
      await pollStatus();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to retry analysis");
    } finally {
      setRetrying(false);
    }
  }

  const steps = job?.steps && job.steps.length > 0 ? job.steps : DEFAULT_STEPS;
  const progress = job?.progress ?? (repo?.analysisStatus === "completed" ? 100 : 5);
  const isCompleted = job?.status === "completed" || repo?.analysisStatus === "completed" || progress >= 100;
  const isFailed = job?.status === "failed" || !!error;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 py-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-mono text-2xl font-semibold tracking-tight">
              {repo?.fullName ?? repoId}
            </h1>
            {repo && (
              <Badge variant="outline" className="text-xs capitalize">
                {repo.analysisStatus.replace("_", " ")}
              </Badge>
            )}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {isCompleted
              ? "Analysis completed! Repository intelligence artifacts are generated."
              : isFailed
              ? "Analysis encountered an issue."
              : "Running live ingestion, AST parsing, dependency graph creation, and ML inference."}
          </p>
        </div>

        {repo && (
          <Button variant="ghost" size="sm" asChild>
            <a
              href={`https://github.com/${repo.fullName}`}
              target="_blank"
              rel="noopener noreferrer"
              className="gap-1.5 text-xs text-muted-foreground hover:text-foreground"
            >
              GitHub <ExternalLink className="size-3" />
            </a>
          </Button>
        )}
      </div>

      <Card className="gap-5 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {!isCompleted && !isFailed && (
              <Loader2 className="size-4 animate-spin text-primary" />
            )}
            {isCompleted && <CheckCircle2 className="size-4 text-risk-low" />}
            {isFailed && <AlertCircle className="size-4 text-risk-critical" />}
            <span className="text-sm font-medium">
              {isCompleted ? "Analysis Complete" : isFailed ? "Analysis Halted" : "Analysis Progress"}
            </span>
          </div>
          <span className="font-mono text-sm tabular-nums text-muted-foreground">
            {progress}%
          </span>
        </div>

        <Progress value={progress} aria-label="Analysis progress" className="h-2" />

        <ul className="flex flex-col gap-3 pt-2" aria-live="polite">
          {steps.map((step) => {
            const isDone = step.status === "done";
            const isActive = step.status === "active";
            const isStepFailed = step.status === "failed";

            return (
              <li key={step.key} className="flex items-start gap-3">
                {isDone && (
                  <CheckCircle2
                    className="mt-0.5 size-4 shrink-0 text-risk-low"
                    aria-hidden="true"
                  />
                )}
                {isActive && (
                  <Loader2
                    className="mt-0.5 size-4 shrink-0 animate-spin text-primary"
                    aria-hidden="true"
                  />
                )}
                {isStepFailed && (
                  <AlertCircle
                    className="mt-0.5 size-4 shrink-0 text-risk-critical"
                    aria-hidden="true"
                  />
                )}
                {!isDone && !isActive && !isStepFailed && (
                  <CircleDashed
                    className="mt-0.5 size-4 shrink-0 text-muted-foreground/40"
                    aria-hidden="true"
                  />
                )}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p
                      className={cn(
                        "text-sm",
                        step.status === "pending" ? "text-muted-foreground" : "text-foreground",
                        isActive && "font-medium text-primary",
                      )}
                    >
                      {step.label}
                    </p>
                    {isDone && (
                      <span className="text-[11px] font-normal text-muted-foreground">Done</span>
                    )}
                    {isActive && (
                      <span className="text-[11px] font-normal text-primary">In progress…</span>
                    )}
                  </div>
                  {step.detail && (
                    <p className="mt-0.5 text-xs text-muted-foreground font-mono">
                      {step.detail}
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </Card>

      {/* Completion card */}
      {isCompleted && (
        <Card className="items-center gap-3 p-6 text-center border-risk-low/40 bg-risk-low/5">
          <PartyPopper className="size-6 text-risk-low" aria-hidden="true" />
          <h2 className="text-base font-semibold">Repository Intelligence is Ready</h2>
          <p className="max-w-md text-xs text-muted-foreground">
            Risk scores calculated by ML inference, dependency graphs, security findings, and PR review insights are now available.
          </p>
          <Button asChild className="mt-2 gap-2">
            <Link href={`/repositories/${repoId}`}>
              {redirecting ? (
                <>
                  <Loader2 className="size-4 animate-spin" /> Redirecting to dashboard…
                </>
              ) : (
                <>
                  Open repository dashboard <ArrowRight className="size-4" />
                </>
              )}
            </Link>
          </Button>
        </Card>
      )}

      {/* Error state */}
      {isFailed && (
        <Card className="items-center gap-3 p-6 text-center border-risk-critical/40 bg-risk-critical/5">
          <AlertCircle className="size-6 text-risk-critical" />
          <h2 className="text-base font-semibold text-risk-critical">Analysis Failed</h2>
          <p className="max-w-md text-xs text-muted-foreground">
            {error || "An error occurred while fetching or analyzing the repository."}
          </p>
          <div className="mt-2 flex gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRetry}
              disabled={retrying}
              className="gap-2"
            >
              {retrying ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <RefreshCw className="size-3.5" />
              )}
              Retry Analysis
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/onboarding">Connect Another Repository</Link>
            </Button>
          </div>
        </Card>
      )}

      {!isCompleted && !isFailed && (
        <p className="text-center text-xs text-muted-foreground">
          Analyzing code files and running machine learning inference. This usually takes 10–45 seconds.
        </p>
      )}
    </div>
  );
}
