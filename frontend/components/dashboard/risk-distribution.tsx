import { riskStyle } from "@/lib/risk";
import type { RiskDistributionEntry } from "@/lib/types";
import { cn } from "@/lib/utils";

export function RiskDistribution({ data }: { data: RiskDistributionEntry[] }) {
  const total = data.reduce((sum, d) => sum + d.count, 0) || 1;

  return (
    <div className="flex flex-col gap-3">
      <div
        className="flex h-2.5 w-full overflow-hidden rounded-full bg-muted"
        role="img"
        aria-label={data
          .map((d) => `${d.count} ${riskStyle(d.level).label} risk components`)
          .join(", ")}
      >
        {data.map((d) => (
          <div
            key={d.level}
            className={cn(riskStyle(d.level).barClass, "h-full first:rounded-l-full last:rounded-r-full")}
            style={{ width: `${(d.count / total) * 100}%` }}
          />
        ))}
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-4">
        {data.map((d) => (
          <div key={d.level} className="flex items-center gap-2">
            <span
              className={cn("size-2 shrink-0 rounded-full", riskStyle(d.level).dotClass)}
              aria-hidden="true"
            />
            <dt className="text-xs text-muted-foreground">{riskStyle(d.level).label}</dt>
            <dd className="ml-auto font-mono text-xs font-medium tabular-nums">{d.count}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
