"use client";

import "reactflow/dist/style.css";
import * as React from "react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  MarkerType,
  MiniMap,
  type Edge,
  type Node,
} from "reactflow";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { GraphNode, type GraphNodeData } from "@/components/graph/graph-node";
import { NodeDetailPanel } from "@/components/graph/node-detail-panel";
import { layoutGraph } from "@/lib/graph-layout";
import { getComponent } from "@/lib/mock-data";
import { riskStyle } from "@/lib/risk";
import { cn } from "@/lib/utils";
import type { GraphEdgeType, GraphNodeType, RepositoryGraph } from "@/lib/types";

const nodeTypes = { graphNode: GraphNode };

const NODE_TYPE_LABELS: Record<GraphNodeType, string> = {
  repository: "Repository",
  file: "File",
  function: "Function",
  class: "Class",
  dependency: "Dependency",
  commit: "Commit",
  pull_request: "Pull request",
};

const EDGE_STYLES: Record<GraphEdgeType, { color: string; dash?: string }> = {
  IMPORTS: { color: "var(--color-chart-1)" },
  CALLS: { color: "var(--color-chart-2)" },
  DEFINES: { color: "var(--color-chart-5)", dash: "6 3" },
  INHERITS: { color: "var(--color-chart-3)", dash: "6 3" },
  DEPENDS_ON: { color: "var(--color-muted-foreground)" },
  MODIFIED_BY: { color: "var(--color-chart-4)", dash: "2 3" },
  CO_CHANGED_WITH: { color: "var(--color-chart-1)", dash: "2 3" },
};

export function DependencyGraph({
  repositoryId,
  graph,
  focusId,
}: {
  repositoryId: string;
  graph: RepositoryGraph;
  focusId?: string;
}) {
  const allNodeTypes = React.useMemo(
    () => Array.from(new Set(graph.nodes.map((n) => n.type))),
    [graph.nodes],
  );
  const [activeTypes, setActiveTypes] = React.useState<Set<GraphNodeType>>(
    () => new Set(allNodeTypes),
  );
  const [selectedId, setSelectedId] = React.useState<string | undefined>(focusId);

  const nodesById = React.useMemo(
    () => new Map(graph.nodes.map((n) => [n.id, n])),
    [graph.nodes],
  );

  const visibleNodes = React.useMemo(
    () => graph.nodes.filter((n) => activeTypes.has(n.type)),
    [graph.nodes, activeTypes],
  );
  const visibleIds = React.useMemo(() => new Set(visibleNodes.map((n) => n.id)), [visibleNodes]);
  const visibleEdges = React.useMemo(
    () => graph.edges.filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target)),
    [graph.edges, visibleIds],
  );

  const rfNodes: Node<GraphNodeData>[] = React.useMemo(() => {
    const base = visibleNodes.map((n) => ({
      id: n.id,
      type: "graphNode",
      data: {
        label: n.label,
        type: n.type,
        riskLevel: n.riskLevel,
        focused: n.id === selectedId,
      },
      position: { x: 0, y: 0 },
    }));
    const edgesForLayout: Edge[] = visibleEdges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
    }));
    return layoutGraph(base, edgesForLayout) as Node<GraphNodeData>[];
  }, [visibleNodes, visibleEdges, selectedId]);

  const rfEdges: Edge[] = React.useMemo(
    () =>
      visibleEdges.map((e) => {
        const style = EDGE_STYLES[e.type];
        return {
          id: e.id,
          source: e.source,
          target: e.target,
          animated: false,
          style: {
            stroke: style.color,
            strokeWidth: 1.5,
            strokeDasharray: style.dash,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: style.color,
            width: 14,
            height: 14,
          },
        };
      }),
    [visibleEdges],
  );

  const selectedNode = selectedId ? nodesById.get(selectedId) : undefined;
  const selectedComponent =
    selectedNode?.type === "file" ? getComponent(selectedNode.id) : undefined;

  function toggleType(type: GraphNodeType) {
    setActiveTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        if (next.size === 1) return next; // keep at least one type visible
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground">Node types:</span>
        {allNodeTypes.map((type) => {
          const active = activeTypes.has(type);
          return (
            <button
              key={type}
              type="button"
              onClick={() => toggleType(type)}
              aria-pressed={active}
              className={cn(
                "rounded-full border px-2.5 py-1 text-xs transition-colors",
                active
                  ? "border-primary/40 bg-primary/10 text-primary"
                  : "border-border text-muted-foreground hover:text-foreground",
              )}
            >
              {NODE_TYPE_LABELS[type]}
            </button>
          );
        })}
        <Button
          variant="ghost"
          size="sm"
          className="ml-auto"
          onClick={() => setActiveTypes(new Set(allNodeTypes))}
        >
          <RotateCcw className="size-3.5" />
          Reset filters
        </Button>
      </div>

      <div className="grid gap-3 lg:grid-cols-[1fr_280px]">
        <Card className="h-[560px] overflow-hidden p-0">
          <ReactFlow
            nodes={rfNodes}
            edges={rfEdges}
            nodeTypes={nodeTypes}
            onNodeClick={(_, node) => setSelectedId(node.id)}
            onPaneClick={() => setSelectedId(undefined)}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            proOptions={{ hideAttribution: true }}
            minZoom={0.3}
          >
            <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="var(--color-border)" />
            <Controls showInteractive={false} />
            <MiniMap
              pannable
              zoomable
              nodeColor={(n) => {
                const data = n.data as GraphNodeData;
                return data.riskLevel ? riskStyle(data.riskLevel).chartColor : "var(--color-muted-foreground)";
              }}
              maskColor="color-mix(in srgb, var(--color-background) 70%, transparent)"
              className="!bg-card"
            />
          </ReactFlow>
        </Card>

        <Card className="h-[560px] gap-0 overflow-hidden p-0">
          {selectedNode ? (
            <NodeDetailPanel
              node={selectedNode}
              edges={graph.edges}
              nodesById={nodesById}
              component={selectedComponent}
              repositoryId={repositoryId}
              onClose={() => setSelectedId(undefined)}
            />
          ) : (
            <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
              <div>
                <p className="text-sm font-medium">Edge legend</p>
                <p className="text-xs text-muted-foreground">
                  Select a node to inspect its relationships.
                </p>
              </div>
              <ul className="flex flex-col gap-2.5">
                {(Object.keys(EDGE_STYLES) as GraphEdgeType[]).map((type) => (
                  <li key={type} className="flex items-center gap-2">
                    <svg width="28" height="8" aria-hidden="true">
                      <line
                        x1="0"
                        y1="4"
                        x2="28"
                        y2="4"
                        stroke={EDGE_STYLES[type].color}
                        strokeWidth={2}
                        strokeDasharray={EDGE_STYLES[type].dash}
                      />
                    </svg>
                    <span className="font-mono text-xs text-muted-foreground">{type}</span>
                  </li>
                ))}
              </ul>
              <div>
                <p className="mb-2 text-xs font-medium text-muted-foreground">Risk color key</p>
                <div className="flex flex-wrap gap-1.5">
                  {(["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const).map((level) => (
                    <Badge key={level} variant="outline" className={riskStyle(level).badgeClass}>
                      {riskStyle(level).label}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
