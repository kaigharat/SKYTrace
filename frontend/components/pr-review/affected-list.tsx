import { ArrowRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { RiskBadge } from "@/components/shared/risk-badge";
import type { AffectedComponent } from "@/lib/types";

export function AffectedList({ items }: { items: AffectedComponent[] }) {
  return (
    <ul className="flex flex-col gap-3">
      {items.map((a) => (
        <li key={a.path} className="flex items-start gap-3">
          <ArrowRight className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-sm">{a.path}</span>
              <Badge variant="outline" className="text-[10px]">
                {a.hops} hop{a.hops > 1 ? "s" : ""} away
              </Badge>
              <RiskBadge level={a.riskLevel} showDot={false} />
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">{a.reason}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}
