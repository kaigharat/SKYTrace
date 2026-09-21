"use client";

import * as React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Loader2,
  Play,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RiskBadge } from "@/components/shared/risk-badge";
import { api } from "@/lib/api";
import type { ComponentRisk } from "@/lib/types";

interface LiveMLInspectorProps {
  initialCode: string;
  componentPath: string;
  componentId: string;
  repositoryId: string;
  initialRisk: ComponentRisk;
}

const SAMPLE_PRESETS = {
  vulnerableBuffer: `// Buffer overflow vulnerability with unchecked string copy
void process_packet(char* packet_data, int length) {
    char internal_buffer[32];
    // Dangerous API: copies without boundary bounds checking
    strcpy(internal_buffer, packet_data);
    gets(internal_buffer);
    free(internal_buffer);
}`,
  insecureAuth: `# Insecure session management & authentication bypass
def authenticate_user(request):
    token = request.headers.get("Authorization")
    # Insecure: signature verification disabled
    payload = jwt.decode(token, verify=False)
    if "admin" in payload.get("roles", []):
        return grant_superuser_access()
    return grant_standard_access()`,
  safeMethod: `# Safe, pure, and robust calculation method
def calculate_tax_breakdown(subtotal: float, tax_rate: float) -> dict:
    if subtotal < 0 or tax_rate < 0:
        raise ValueError("Inputs must be non-negative numbers")
    tax_amount = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax_amount, 2)
    return {
        "subtotal": subtotal,
        "tax_amount": tax_amount,
        "total": total,
    }`,
};

export function LiveMLInspector({
  initialCode,
  componentPath,
  componentId,
  repositoryId,
  initialRisk,
}: LiveMLInspectorProps) {
  const [code, setCode] = React.useState(initialCode);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<ComponentRisk | null>(initialRisk);
  const [latencyMs, setLatencyMs] = React.useState<number | null>(null);

  async function handleRunInference() {
    setLoading(true);
    setError(null);
    const start = performance.now();

    try {
      const response = await api.predictCode({
        code,
        path: componentPath,
        language: componentPath.endsWith(".c") ? "C" : "Python",
        repositoryId,
        componentId,
      });
      const duration = Math.round(performance.now() - start);
      setLatencyMs(duration);
      setResult(response.component);
    } catch (err: any) {
      setError(
        err?.message ||
          "Could not reach FastAPI ML backend at http://localhost:8000. Ensure the backend server is running.",
      );
    } finally {
      setLoading(false);
    }
  }

  function handleLoadPreset(presetKey: keyof typeof SAMPLE_PRESETS) {
    setCode(SAMPLE_PRESETS[presetKey]);
  }

  function handleReset() {
    setCode(initialCode);
    setResult(initialRisk);
    setError(null);
    setLatencyMs(null);
  }

  return (
    <Card className="border-primary/20 bg-card/60 backdrop-blur-sm">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Cpu className="size-5 text-primary animate-pulse" />
            <CardTitle className="text-base font-semibold">
              Live ML Risk Predictor (Real-Time Inference)
            </CardTitle>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline" className="font-mono text-[10px]">
              RandomForestBaseline + 39 Static Features
            </Badge>
            {latencyMs !== null && (
              <Badge variant="secondary" className="font-mono text-[10px] text-emerald-400">
                {latencyMs}ms latency
              </Badge>
            )}
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          Modify the code below or choose a sample to run live ML feature extraction, defect
          scoring, and explainability generation via the FastAPI backend.
        </p>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        {/* Preset Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground">Load test pattern:</span>
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            onClick={() => handleLoadPreset("vulnerableBuffer")}
          >
            Vulnerable Buffer (C)
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            onClick={() => handleLoadPreset("insecureAuth")}
          >
            Insecure Auth (Python)
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            onClick={() => handleLoadPreset("safeMethod")}
          >
            Safe Helper (Python)
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs text-muted-foreground ml-auto"
            onClick={handleReset}
          >
            <RotateCcw className="size-3 mr-1" />
            Reset
          </Button>
        </div>

        {/* Code Input */}
        <div className="relative rounded-lg border bg-zinc-950/80 p-2 font-mono text-xs">
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            rows={8}
            className="w-full resize-y bg-transparent font-mono text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-0"
            placeholder="Paste code snippet to analyze..."
          />
        </div>

        {/* Action Button */}
        <div className="flex items-center justify-between">
          <div className="text-xs text-muted-foreground">
            {loading ? (
              <span className="flex items-center gap-1.5 text-primary">
                <Loader2 className="size-3.5 animate-spin" />
                Extracting features & running ML forward pass...
              </span>
            ) : (
              <span>Ready for inference against backend model</span>
            )}
          </div>

          <Button
            onClick={handleRunInference}
            disabled={loading}
            className="gap-2 font-medium"
          >
            {loading ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Play className="size-4 fill-current" />
                Run Real ML Inference
              </>
            )}
          </Button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive flex items-start gap-2">
            <AlertTriangle className="size-4 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Inference Error</p>
              <p className="mt-0.5 opacity-90">{error}</p>
            </div>
          </div>
        )}

        {/* Prediction Results Display */}
        {result && (
          <div className="rounded-lg border bg-zinc-900/40 p-4 flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/40 pb-3">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="size-4 text-emerald-400" />
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Latest ML Prediction Results
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">Assigned Risk:</span>
                <RiskBadge level={result.riskLevel} />
              </div>
            </div>

            {/* Score Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="rounded-md border bg-background/50 p-3">
                <div className="text-xs text-muted-foreground">Defect Risk</div>
                <div className="mt-1 flex items-baseline justify-between">
                  <span className="text-2xl font-bold">{result.defectRisk}%</span>
                  <span className="text-[10px] text-muted-foreground">Code complexity</span>
                </div>
                <div className="mt-2 h-1.5 w-full rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full bg-amber-500 rounded-full transition-all duration-500"
                    style={{ width: `${result.defectRisk}%` }}
                  />
                </div>
              </div>

              <div className="rounded-md border bg-background/50 p-3">
                <div className="text-xs text-muted-foreground">Security Risk</div>
                <div className="mt-1 flex items-baseline justify-between">
                  <span className="text-2xl font-bold">{result.securityRisk}%</span>
                  <span className="text-[10px] text-muted-foreground">Vulnerability</span>
                </div>
                <div className="mt-2 h-1.5 w-full rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full bg-red-500 rounded-full transition-all duration-500"
                    style={{ width: `${result.securityRisk}%` }}
                  />
                </div>
              </div>

              <div className="rounded-md border bg-background/50 p-3">
                <div className="text-xs text-muted-foreground">Regression Risk</div>
                <div className="mt-1 flex items-baseline justify-between">
                  <span className="text-2xl font-bold">{result.regressionRisk}%</span>
                  <span className="text-[10px] text-muted-foreground">Blast radius</span>
                </div>
                <div className="mt-2 h-1.5 w-full rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full transition-all duration-500"
                    style={{ width: `${result.regressionRisk}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Explainable Evidence */}
            {result.evidence && result.evidence.length > 0 && (
              <div className="flex flex-col gap-2">
                <span className="text-xs font-semibold text-muted-foreground">
                  AI Explainability Factors (Why is this scored this way?):
                </span>
                <div className="flex flex-col gap-2">
                  {result.evidence.map((factor, idx) => (
                    <div
                      key={idx}
                      className="rounded-md border border-border/60 bg-background/30 p-2.5 text-xs flex flex-col gap-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-foreground">{factor.label}</span>
                        <span className="font-mono text-[11px] text-primary">
                          +{Math.round(factor.weight * 100)}% contribution
                        </span>
                      </div>
                      <p className="text-muted-foreground text-[11px]">{factor.detail}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
