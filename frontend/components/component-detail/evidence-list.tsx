import type { EvidenceFactor } from "@/lib/types";

export function EvidenceList({ evidence }: { evidence: EvidenceFactor[] }) {
  return (
    <ul className="flex flex-col gap-4">
      {evidence.map((e) => (
        <li key={e.label}>
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-medium">{e.label}</p>
            <span className="shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
              {Math.round(e.weight * 100)}% of score
            </span>
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground">{e.detail}</p>
          <div
            className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted"
            role="presentation"
          >
            <div
              className="h-full rounded-full bg-primary"
              style={{ width: `${e.weight * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
