import { ArrowRight, FlaskConical } from "lucide-react";
import { RiskBadge } from "@/components/shared/risk-badge";
import type { RecommendedTest } from "@/lib/types";

export function TestRecommendations({ tests }: { tests: RecommendedTest[] }) {
  return (
    <ul className="flex flex-col gap-3">
      {tests.map((t) => (
        <li key={t.name} className="flex items-start gap-3">
          <FlaskConical className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium">{t.name}</span>
              <RiskBadge level={t.priority} showDot={false} />
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">{t.reason}</p>
            <p className="mt-1 flex items-center gap-1 font-mono text-[11px] text-primary">
              <ArrowRight className="size-3" />
              {t.suite}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}
