import { riskLevelFromScore, riskStyle } from "@/lib/risk";
import { cn } from "@/lib/utils";

function RiskMeter({ label, value }: { label: string; value: number }) {
  const level = riskLevelFromScore(value);
  const style = riskStyle(level);
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className={cn("font-mono font-semibold tabular-nums", style.textClass)}>
          {value}%
        </span>
      </div>
      <div
        role="meter"
        aria-label={`${label}: ${value} out of 100, ${style.label} risk`}
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-2.5 w-full overflow-hidden rounded-full bg-muted"
      >
        <div
          className={cn("h-full rounded-full transition-[width] duration-500", style.barClass)}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

export function RiskScorePanel({
  defectRisk,
  securityRisk,
  regressionRisk,
}: {
  defectRisk: number;
  securityRisk: number;
  regressionRisk: number;
}) {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <RiskMeter label="Defect risk" value={defectRisk} />
      <RiskMeter label="Security risk" value={securityRisk} />
      <RiskMeter label="Regression risk" value={regressionRisk} />
    </div>
  );
}
