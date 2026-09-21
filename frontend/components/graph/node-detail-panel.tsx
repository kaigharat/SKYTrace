import Link from "next/link";
import { ExternalLink, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RiskBadge } from "@/components/shared/risk-badge";
import type { ComponentRisk, RepoGraphEdge, RepoGraphNode } from "@/lib/types";
import { cn } from "@/lib/utils";

export function NodeDetailPanel({
  node,
  edges,
  nodesById,
  component,
  repositoryId,
  onClose,
}: {
  node: RepoGraphNode;
  edges: RepoGraphEdge[];
  nodesById: Map<string, RepoGraphNode>;
  component?: ComponentRisk;
  repositoryId: string;
  onClose: () => void;
}) {
  const outgoing = edges.filter((e) => e.source === node.id);
  const incoming = edges.filter((e) => e.target === node.id);

  return (
    <div className="flex h-full w-full flex-col gap-4 overflow-y-auto p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate font-mono text-sm font-semibold">{node.label}</p>
          <p className="text-xs capitalize text-muted-foreground">{node.type.replace("_", " ")}</p>
        </div>
        <Button variant="ghost" size="icon" className="size-7 shrink-0" onClick={onClose} aria-label="Close panel">
          <X className="size-4" />
        </Button>
      </div>

      {component && (
        <div className="flex flex-col gap-2 rounded-lg border border-border bg-muted/20 p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Overall risk</span>
            <RiskBadge level={component.riskLevel} />
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-[10px] text-muted-foreground">Defect</p>
              <p className="font-mono text-sm font-medium">{component.defectRisk}</p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">Security</p>
              <p className="font-mono text-sm font-medium">{component.securityRisk}</p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">Regression</p>
              <p className="font-mono text-sm font-medium">{component.regressionRisk}</p>
            </div>
          </div>
          <Button size="sm" variant="outline" asChild className="mt-1">
            <Link href={`/repositories/${repositoryId}/components/${component.id}`}>
              Open component detail
              <ExternalLink className="size-3.5" />
            </Link>
          </Button>
        </div>
      )}

      <div>
        <p className="mb-2 text-xs font-medium text-muted-foreground">
          Outgoing relationships · {outgoing.length}
        </p>
        <ul className="flex flex-col gap-1.5">
          {outgoing.map((e) => {
            const target = nodesById.get(e.target);
            return (
              <li key={e.id} className="flex items-center justify-between gap-2 text-xs">
                <span className="truncate font-mono">{target?.label ?? e.target}</span>
                <span className={cn("shrink-0 rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground")}>
                  {e.type}
                </span>
              </li>
            );
          })}
          {outgoing.length === 0 && (
            <li className="text-xs text-muted-foreground">None</li>
          )}
        </ul>
      </div>

      <div>
        <p className="mb-2 text-xs font-medium text-muted-foreground">
          Incoming relationships · {incoming.length}
        </p>
        <ul className="flex flex-col gap-1.5">
          {incoming.map((e) => {
            const source = nodesById.get(e.source);
            return (
              <li key={e.id} className="flex items-center justify-between gap-2 text-xs">
                <span className="truncate font-mono">{source?.label ?? e.source}</span>
                <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                  {e.type}
                </span>
              </li>
            );
          })}
          {incoming.length === 0 && (
            <li className="text-xs text-muted-foreground">None</li>
          )}
        </ul>
      </div>
    </div>
  );
}
