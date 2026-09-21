import { Bug, GitCommitHorizontal, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { SimilarPattern } from "@/lib/types";
import { formatDate } from "@/lib/format";

const TYPE_ICON = {
  bug: Bug,
  vulnerability: ShieldAlert,
  change: GitCommitHorizontal,
} as const;

const TYPE_LABEL = {
  bug: "Historical bug",
  vulnerability: "Historical vulnerability",
  change: "Historical change",
} as const;

export function SimilarPatterns({ patterns }: { patterns: SimilarPattern[] }) {
  if (patterns.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        No similar historical patterns found above the similarity threshold.
      </p>
    );
  }

  return (
    <ul className="flex flex-col divide-y divide-border">
      {patterns.map((p) => {
        const Icon = TYPE_ICON[p.type];
        return (
          <li key={p.id} className="flex items-start gap-3 py-4 first:pt-0 last:pb-0">
            <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-medium">{p.title}</p>
                <Badge variant="outline" className="text-[10px]">
                  {TYPE_LABEL[p.type]}
                </Badge>
              </div>
              <p className="mt-0.5 text-xs text-muted-foreground">{p.summary}</p>
              <div className="mt-1.5 flex items-center gap-3 text-[11px] text-muted-foreground">
                <span className="font-mono">{p.repo}</span>
                <span>{formatDate(p.date)}</span>
                <span className="font-mono font-medium text-primary">
                  {Math.round(p.similarity * 100)}% similar
                </span>
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
