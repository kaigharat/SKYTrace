import { cn } from "@/lib/utils";
import { riskStyle } from "@/lib/risk";
import type { RiskLevel } from "@/lib/types";

export function RiskBadge({
  level,
  className,
  showDot = true,
}: {
  level: RiskLevel;
  className?: string;
  showDot?: boolean;
}) {
  const style = riskStyle(level);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium tabular-nums",
        style.badgeClass,
        className,
      )}
    >
      {showDot && (
        <span
          aria-hidden="true"
          className={cn("size-1.5 rounded-full", style.dotClass)}
        />
      )}
      {style.label}
    </span>
  );
}
