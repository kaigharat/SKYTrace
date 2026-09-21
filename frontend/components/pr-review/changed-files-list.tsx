import { ArrowRight } from "lucide-react";
import { RiskBadge } from "@/components/shared/risk-badge";
import type { ChangedFile } from "@/lib/types";

export function ChangedFilesList({ files }: { files: ChangedFile[] }) {
  return (
    <ul className="flex flex-col gap-2.5">
      {files.map((f) => (
        <li key={f.path} className="flex items-center gap-3">
          <ArrowRight className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
          <span className="min-w-0 flex-1 truncate font-mono text-sm">{f.path}</span>
          <span className="shrink-0 font-mono text-xs tabular-nums text-risk-low">+{f.additions}</span>
          <span className="shrink-0 font-mono text-xs tabular-nums text-risk-critical">-{f.deletions}</span>
          <RiskBadge level={f.riskLevel} showDot={false} className="shrink-0" />
        </li>
      ))}
    </ul>
  );
}
