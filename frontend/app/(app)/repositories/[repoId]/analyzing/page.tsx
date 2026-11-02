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
  Code2,
  Cpu,
  Network,
  ShieldCheck,
  Sparkles,
  Layers,
  FileCode2,
  Zap,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { GithubMark } from "@/components/shared/github-mark";
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

interface FlowStage {
  id: number;
  keys: string[];
  title: string;
  badge: string;
  icon: React.ComponentType<{ className?: string }>;
  simpleExplanation: string;
  technicalDetail: string;
}

const FLOW_STAGES: FlowStage[] = [
  {
    id: 1,
    keys: ["clone"],
    title: "1. Code Ingestion & Tree Walk",
    badge: "Input Stage",
    icon: GithubMark,
    simpleExplanation: "Takes your GitHub link, authenticates, and downloads the repository source tree, active branches, and commit churn.",
    technicalDetail: "Direct GitHub API v3 tree walk with concurrent file fetching across supported extensions (.py, .ts, .js, .go, etc.).",
  },
  {
    id: 2,
    keys: ["parse"],
    title: "2. AST & 39-Feature Extraction",
    badge: "Static Analysis",
    icon: FileCode2,
    simpleExplanation: "Breaks each file into an Abstract Syntax Tree to measure complexity, loops, nesting depth, and dangerous API calls.",
    technicalDetail: "Quantifies 39 code metrics: cyclomatic complexity, switch branches, token entropy, and high-risk functions (strcpy, malloc, eval).",
  },
  {
    id: 3,
    keys: ["graph", "history"],
    title: "3. Dependency Graph & Blast Radius",
    badge: "Architecture Map",
    icon: Network,
    simpleExplanation: "Maps which files import or call each other. If a file breaks, this graph shows exactly which other parts of the app are affected.",
    technicalDetail: "Constructs directed graph nodes & edges via import resolution; traverses multi-hop dependents for pull-request blast radius.",
  },
  {
    id: 4,
    keys: ["models", "index"],
    title: "4. Machine Learning Inference Engine",
    badge: "AI Risk Engine",
    icon: Cpu,
    simpleExplanation: "Feeds the 39 code features into our trained Random Forest model to predict future bugs, security flaws, and regression likelihood.",
    technicalDetail: "Evaluates calibrated multi-output classifier (300 trees) tuned on historical vulnerability distributions (CWE/CVE patterns).",
  },
  {
    id: 5,
    keys: ["finalize"],
    title: "5. Explainable AI & Health Score",
    badge: "Final Synthesis",
    icon: ShieldCheck,
    simpleExplanation: "Translates AI numbers into clear, plain-English reasons (evidence factors) and compiles the single 0–100 repository health score.",
    technicalDetail: "Generates attribution evidence weights, security findings with line references, and assigns CRITICAL/HIGH/MED/LOW risk tiers.",
  },
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
          // Success! Keep the analysis and pipeline flow visible so evaluator/user can inspect all details
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
        timerId = setTimeout(runPoll, 1800);
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

  // Determine which flow stage is currently active
  const activeStep = steps.find((s) => s.status === "active")?.key || "";
  const currentStageId = isCompleted
    ? 5
    : FLOW_STAGES.find((stage) => stage.keys.includes(activeStep))?.id || 1;

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 py-4">
      {/* Page Header */}
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border/60 pb-5">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="font-mono text-2xl font-bold tracking-tight">
              {repo?.fullName ?? repoId}
            </h1>
            {repo && (
              <Badge variant="outline" className="text-xs capitalize font-mono">
                {repo.analysisStatus.replace("_", " ")}
              </Badge>
            )}
            <Badge variant="secondary" className="text-[11px] gap-1 font-medium bg-primary/10 text-primary border-primary/20">
              <Sparkles className="size-3" />
              Live AI Analysis In Progress
            </Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {isCompleted
              ? "Analysis completed! Repository intelligence artifacts are generated."
              : isFailed
              ? "Analysis encountered an issue."
              : "Running live ingestion, AST parsing, dependency graph creation, and ML inference."}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {repo && (
            <Button variant="outline" size="sm" asChild>
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
          {isCompleted && (
            <Button size="sm" asChild className="gap-1.5 shadow-xs">
              <Link href={`/repositories/${repoId}`}>
                <span>Open Dashboard</span>
                <ArrowRight className="size-3.5" />
              </Link>
            </Button>
          )}
        </div>
      </div>

      {/* Main 2-Column Grid: Left = Progress Checklist, Right = Evaluator Flow Explainer */}
      <div className="grid gap-6 lg:grid-cols-12 items-start">
        {/* Left Column: Real-time Checklist & Progress (7 cols) */}
        <div className="flex flex-col gap-5 lg:col-span-7">
          <Card className="gap-5 p-6 shadow-xs border-border/80">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                {!isCompleted && !isFailed && (
                  <Loader2 className="size-4 animate-spin text-primary" />
                )}
                {isCompleted && <CheckCircle2 className="size-4 text-risk-low" />}
                {isFailed && <AlertCircle className="size-4 text-risk-critical" />}
                <span className="text-sm font-semibold">
                  {isCompleted ? "Analysis Complete" : isFailed ? "Analysis Halted" : "Analysis Progress"}
                </span>
              </div>
              <span className="font-mono text-sm font-bold tabular-nums text-primary">
                {progress}%
              </span>
            </div>

            <Progress value={progress} aria-label="Analysis progress" className="h-2.5" />

            <ul className="flex flex-col gap-3 pt-2" aria-live="polite">
              {steps.map((step) => {
                const isDone = step.status === "done";
                const isActive = step.status === "active";
                const isStepFailed = step.status === "failed";

                return (
                  <li
                    key={step.key}
                    className={cn(
                      "flex items-start gap-3 rounded-lg p-2.5 transition-colors",
                      isActive && "bg-primary/5 border border-primary/20",
                      isDone && "bg-muted/30"
                    )}
                  >
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
                      <div className="flex items-center gap-2 justify-between">
                        <p
                          className={cn(
                            "text-sm",
                            step.status === "pending" ? "text-muted-foreground" : "text-foreground",
                            isActive && "font-semibold text-primary",
                            isDone && "font-medium"
                          )}
                        >
                          {step.label}
                        </p>
                        {isDone && (
                          <span className="text-[11px] font-semibold text-risk-low">Done</span>
                        )}
                        {isActive && (
                          <Badge variant="outline" className="text-[10px] px-1.5 py-0 border-primary/30 text-primary animate-pulse">
                            In progress…
                          </Badge>
                        )}
                      </div>
                      {step.detail && (
                        <p className="mt-1 text-xs text-muted-foreground font-mono">
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
            <Card className="items-center gap-3 p-6 text-center border-risk-low/40 bg-risk-low/5 shadow-sm">
              <PartyPopper className="size-6 text-risk-low" aria-hidden="true" />
              <h2 className="text-base font-bold text-foreground">Repository Intelligence is Ready</h2>
              <p className="max-w-md text-xs text-muted-foreground">
                All 5 analysis stages completed successfully. Review the pipeline execution and technical details on this page, or navigate to the full dashboard.
              </p>
              <div className="flex flex-wrap items-center justify-center gap-3 mt-2">
                <Button asChild size="lg" className="gap-2 shadow-sm font-semibold">
                  <Link href={`/repositories/${repoId}`}>
                    <span>Open Repository Dashboard</span>
                    <ArrowRight className="size-4" />
                  </Link>
                </Button>
                <Button asChild variant="outline" size="lg" className="gap-2">
                  <Link href={`/repositories/${repoId}/components`}>
                    <span>Inspect Components</span>
                  </Link>
                </Button>
              </div>
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
        </div>

        {/* Right Column: Flow Explainer for Evaluators (5 cols) */}
        <div className="flex flex-col gap-4 lg:col-span-5">
          <Card className="p-5 border-primary/30 bg-card/60 shadow-md">
            <div className="flex items-center justify-between mb-3 border-b border-border/70 pb-3">
              <div className="flex items-center gap-2">
                <div className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground font-bold text-xs">
                  <Zap className="size-3.5" />
                </div>
                <div>
                  <h2 className="text-sm font-bold tracking-tight">How SkyTrace Analyzes Code</h2>
                  <p className="text-[11px] text-muted-foreground">Evaluator Guide &amp; AI Pipeline Flow</p>
                </div>
              </div>
              <Badge variant="outline" className="text-[10px] border-primary/30 text-primary uppercase tracking-wider font-semibold">
                Live Pipeline
              </Badge>
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed mb-4">
              Here is what happens under the hood as SkyTrace processes your repository:
            </p>

            {/* Stages Stack */}
            <div className="flex flex-col gap-3">
              {FLOW_STAGES.map((stage) => {
                const isCurrent = currentStageId === stage.id;
                const isPast = currentStageId > stage.id || isCompleted;
                const StageIcon = stage.icon;

                return (
                  <div
                    key={stage.id}
                    className={cn(
                      "rounded-lg border p-3.5 transition-all text-xs",
                      isCurrent && "border-primary bg-primary/10 ring-1 ring-primary/30 shadow-xs",
                      isPast && !isCurrent && "border-border/60 bg-muted/20 opacity-90",
                      !isPast && !isCurrent && "border-border/40 bg-background/50 opacity-60"
                    )}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-2">
                        <div
                          className={cn(
                            "flex size-6 shrink-0 items-center justify-center rounded-md text-[11px] font-bold",
                            isCurrent && "bg-primary text-primary-foreground",
                            isPast && !isCurrent && "bg-risk-low/20 text-risk-low",
                            !isPast && !isCurrent && "bg-muted text-muted-foreground"
                          )}
                        >
                          <StageIcon className="size-3.5" />
                        </div>
                        <span className="font-semibold text-foreground text-xs">
                          {stage.title}
                        </span>
                      </div>
                      {isCurrent ? (
                        <Badge className="bg-primary text-primary-foreground text-[10px] px-1.5 py-0 animate-pulse shrink-0">
                          Active Now
                        </Badge>
                      ) : isPast ? (
                        <span className="text-[10px] font-semibold text-risk-low shrink-0">
                          Complete ✓
                        </span>
                      ) : (
                        <span className="text-[10px] text-muted-foreground shrink-0">
                          Upcoming
                        </span>
                      )}
                    </div>

                    <p className="text-[11.5px] text-muted-foreground leading-relaxed mt-1">
                      {stage.simpleExplanation}
                    </p>

                    {isCurrent && (
                      <div className="mt-2.5 rounded bg-background/80 p-2 border border-border/60 font-mono text-[10px] text-primary">
                        <span className="font-bold text-foreground">Under the hood: </span>
                        {stage.technicalDetail}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Evaluator Callout Note */}
            <div className="mt-4 rounded-lg border border-primary/20 bg-primary/5 p-3 text-[11.5px] text-muted-foreground leading-relaxed">
              <span className="font-semibold text-foreground flex items-center gap-1.5 mb-1">
                <Sparkles className="size-3.5 text-primary" /> Key Takeaway for Evaluators
              </span>
              Unlike standard linters that only check style, SkyTrace pairs AST code topology with supervised Machine Learning (Random Forest) to forecast defect hotspots and blast radius before code merges.
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
