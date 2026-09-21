import type { RiskLevel } from "@/lib/types";

export const RISK_LEVELS: RiskLevel[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

export function riskLevelFromScore(score: number): RiskLevel {
  if (score >= 85) return "CRITICAL";
  if (score >= 65) return "HIGH";
  if (score >= 35) return "MEDIUM";
  return "LOW";
}

interface RiskStyle {
  badgeClass: string;
  dotClass: string;
  textClass: string;
  barClass: string;
  chartColor: string;
  label: string;
}

const RISK_STYLES: Record<RiskLevel, RiskStyle> = {
  CRITICAL: {
    badgeClass:
      "bg-risk-critical/15 text-risk-critical border-risk-critical/30",
    dotClass: "bg-risk-critical",
    textClass: "text-risk-critical",
    barClass: "bg-risk-critical",
    chartColor: "var(--risk-critical)",
    label: "Critical",
  },
  HIGH: {
    badgeClass: "bg-risk-high/15 text-risk-high border-risk-high/30",
    dotClass: "bg-risk-high",
    textClass: "text-risk-high",
    barClass: "bg-risk-high",
    chartColor: "var(--risk-high)",
    label: "High",
  },
  MEDIUM: {
    badgeClass: "bg-risk-medium/15 text-risk-medium border-risk-medium/30",
    dotClass: "bg-risk-medium",
    textClass: "text-risk-medium",
    barClass: "bg-risk-medium",
    chartColor: "var(--risk-medium)",
    label: "Medium",
  },
  LOW: {
    badgeClass: "bg-risk-low/15 text-risk-low border-risk-low/30",
    dotClass: "bg-risk-low",
    textClass: "text-risk-low",
    barClass: "bg-risk-low",
    chartColor: "var(--risk-low)",
    label: "Low",
  },
};

export function riskStyle(level: RiskLevel): RiskStyle {
  return RISK_STYLES[level];
}

export function healthScoreLabel(score: number): string {
  if (score >= 80) return "Healthy";
  if (score >= 60) return "Needs attention";
  if (score >= 40) return "At risk";
  return "Critical";
}

export function healthScoreTextClass(score: number): string {
  if (score >= 80) return "text-risk-low";
  if (score >= 60) return "text-risk-medium";
  if (score >= 40) return "text-risk-high";
  return "text-risk-critical";
}

export function healthScoreBarClass(score: number): string {
  if (score >= 80) return "bg-risk-low";
  if (score >= 60) return "bg-risk-medium";
  if (score >= 40) return "bg-risk-high";
  return "bg-risk-critical";
}
