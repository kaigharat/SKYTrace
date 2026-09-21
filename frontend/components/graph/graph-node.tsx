import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import {
  Boxes,
  FileCode2,
  FunctionSquare,
  GitCommitHorizontal,
  GitPullRequest,
  Package,
  Shapes,
} from "lucide-react";
import type { GraphNodeType } from "@/lib/types";
import { riskStyle } from "@/lib/risk";
import { cn } from "@/lib/utils";

const TYPE_ICON: Record<GraphNodeType, typeof FileCode2> = {
  repository: Boxes,
  file: FileCode2,
  function: FunctionSquare,
  class: Shapes,
  dependency: Package,
  commit: GitCommitHorizontal,
  pull_request: GitPullRequest,
};

export interface GraphNodeData {
  label: string;
  type: GraphNodeType;
  riskLevel?: import("@/lib/types").RiskLevel;
  dimmed?: boolean;
  focused?: boolean;
}

function GraphNodeComponent({ data }: NodeProps<GraphNodeData>) {
  const Icon = TYPE_ICON[data.type];
  const style = data.riskLevel ? riskStyle(data.riskLevel) : null;

  return (
    <div
      className={cn(
        "flex min-w-[160px] items-center gap-2 rounded-lg border bg-card px-3 py-2 shadow-sm transition-opacity",
        data.focused ? "border-primary ring-2 ring-primary/40" : "border-border",
        data.dimmed && "opacity-30",
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-border" />
      <span
        className={cn(
          "flex size-6 shrink-0 items-center justify-center rounded-md",
          style ? style.badgeClass : "bg-muted text-muted-foreground",
        )}
        aria-hidden="true"
      >
        <Icon className="size-3.5" />
      </span>
      <div className="min-w-0">
        <p className="truncate font-mono text-xs font-medium">{data.label}</p>
        <p className="text-[10px] capitalize text-muted-foreground">
          {data.type.replace("_", " ")}
        </p>
      </div>
      <Handle type="source" position={Position.Right} className="!bg-border" />
    </div>
  );
}

export const GraphNode = memo(GraphNodeComponent);
