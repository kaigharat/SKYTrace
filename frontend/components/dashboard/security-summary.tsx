import Link from "next/link";
import { ShieldAlert } from "lucide-react";
import { RiskBadge } from "@/components/shared/risk-badge";
import type { SecurityFinding } from "@/lib/types";

export function SecuritySummary({
  repositoryId,
  findings,
}: {
  repositoryId: string;
  findings: SecurityFinding[];
}) {
  if (findings.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        No open security findings.
      </p>
    );
  }

  return (
    <ul className="flex flex-col divide-y divide-border">
      {findings.map((f) => (
        <li key={f.id} className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
          <ShieldAlert className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium">{f.category}</span>
              <RiskBadge level={f.severity} />
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">{f.description}</p>
            <Link
              href={`/repositories/${repositoryId}/components/${f.componentId}`}
              className="mt-1 inline-flex font-mono text-[11px] text-primary hover:underline"
            >
              {f.file}:{f.line}
            </Link>
          </div>
        </li>
      ))}
    </ul>
  );
}
