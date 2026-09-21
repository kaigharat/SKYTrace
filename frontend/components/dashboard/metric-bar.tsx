import { cn } from "@/lib/utils";
import { healthScoreBarClass, healthScoreTextClass } from "@/lib/risk";

export function MetricBar({
  label,
  value,
  target = 80,
}: {
  label: string;
  value: number;
  target?: number;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className={cn("font-mono font-medium tabular-nums", healthScoreTextClass(value))}>
          {value}
        </span>
      </div>
      <div
        role="meter"
        aria-label={label}
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
        className="relative h-2 w-full overflow-hidden rounded-full bg-muted"
      >
        <div
          className={cn("h-full rounded-full transition-[width] duration-500", healthScoreBarClass(value))}
          style={{ width: `${value}%` }}
        />
        <div
          className="absolute top-0 h-full w-0.5 bg-foreground/40"
          style={{ left: `${target}%` }}
          aria-hidden="true"
        />
      </div>
    </div>
  );
}
