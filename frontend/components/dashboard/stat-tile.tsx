import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function StatTile({
  icon: Icon,
  label,
  value,
  tone = "default",
}: {
  icon: LucideIcon;
  label: string;
  value: number | string;
  tone?: "default" | "critical" | "high" | "medium";
}) {
  return (
    <div className="flex flex-col gap-1.5 rounded-lg border border-border bg-muted/20 p-3">
      <div className="flex items-center gap-1.5 text-muted-foreground">
        <Icon className="size-3.5" aria-hidden="true" />
        <span className="text-[11px]">{label}</span>
      </div>
      <span
        className={cn(
          "font-mono text-xl font-semibold tabular-nums",
          tone === "critical" && "text-risk-critical",
          tone === "high" && "text-risk-high",
          tone === "medium" && "text-risk-medium",
        )}
      >
        {value}
      </span>
    </div>
  );
}
