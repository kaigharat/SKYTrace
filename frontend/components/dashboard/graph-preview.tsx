import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type { RepositoryGraph } from "@/lib/types";
import { riskStyle } from "@/lib/risk";

const PREVIEW_LAYOUT = [
  { x: 20, y: 55 },
  { x: 85, y: 20 },
  { x: 85, y: 90 },
  { x: 150, y: 15 },
  { x: 150, y: 55 },
  { x: 150, y: 95 },
  { x: 215, y: 40 },
  { x: 215, y: 75 },
];

export function GraphPreview({
  repositoryId,
  graph,
}: {
  repositoryId: string;
  graph: RepositoryGraph;
}) {
  const nodes = graph.nodes.slice(0, PREVIEW_LAYOUT.length).map((n, i) => ({
    ...n,
    ...PREVIEW_LAYOUT[i],
  }));
  const nodeIds = new Set(nodes.map((n) => n.id));
  const edges = graph.edges.filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target));

  return (
    <Link
      href={`/repositories/${repositoryId}/graph`}
      className="group flex flex-col gap-3 rounded-lg border border-border bg-muted/20 p-4 transition-colors hover:border-primary/40 hover:bg-muted/40"
    >
      <svg
        viewBox="0 0 240 110"
        className="h-24 w-full"
        aria-hidden="true"
        focusable="false"
      >
        {edges.map((e) => {
          const source = nodes.find((n) => n.id === e.source);
          const target = nodes.find((n) => n.id === e.target);
          if (!source || !target) return null;
          return (
            <line
              key={e.id}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              stroke="var(--color-border)"
              strokeWidth={1.5}
            />
          );
        })}
        {nodes.map((n) => (
          <circle
            key={n.id}
            cx={n.x}
            cy={n.y}
            r={n.type === "repository" ? 6 : 5}
            fill={n.riskLevel ? riskStyle(n.riskLevel).chartColor : "var(--color-muted-foreground)"}
            opacity={0.9}
          />
        ))}
      </svg>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">
          {graph.nodes.length} nodes · {graph.edges.length} relationships
        </span>
        <span className="flex items-center gap-1 font-medium text-primary">
          Open dependency graph
          <ArrowRight className="size-3 transition-transform group-hover:translate-x-0.5" />
        </span>
      </div>
    </Link>
  );
}
