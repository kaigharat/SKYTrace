import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RiskBadge } from "@/components/shared/risk-badge";
import type { ComponentRisk } from "@/lib/types";
import { formatRelativeDate } from "@/lib/format";
import { cn } from "@/lib/utils";

function ScoreCell({ value }: { value: number }) {
  return (
    <span
      className={cn(
        "font-mono text-xs tabular-nums",
        value >= 80 && "text-risk-critical",
        value >= 55 && value < 80 && "text-risk-high",
        value >= 30 && value < 55 && "text-risk-medium",
        value < 30 && "text-risk-low",
      )}
    >
      {value}
    </span>
  );
}

export function ComponentsTable({
  repositoryId,
  components,
}: {
  repositoryId: string;
  components: ComponentRisk[];
}) {
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Component</TableHead>
            <TableHead>Risk</TableHead>
            <TableHead className="text-right">Defect</TableHead>
            <TableHead className="text-right">Security</TableHead>
            <TableHead className="text-right">Regression</TableHead>
            <TableHead className="text-right">Modified</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {components.map((c) => (
            <TableRow key={c.id} className="group">
              <TableCell className="max-w-[220px]">
                <Link
                  href={`/repositories/${repositoryId}/components/${c.id}`}
                  className="truncate font-mono text-xs underline-offset-4 group-hover:text-primary group-hover:underline"
                >
                  {c.path}
                </Link>
              </TableCell>
              <TableCell>
                <RiskBadge level={c.riskLevel} />
              </TableCell>
              <TableCell className="text-right">
                <ScoreCell value={c.defectRisk} />
              </TableCell>
              <TableCell className="text-right">
                <ScoreCell value={c.securityRisk} />
              </TableCell>
              <TableCell className="text-right">
                <ScoreCell value={c.regressionRisk} />
              </TableCell>
              <TableCell className="text-right text-xs text-muted-foreground">
                {formatRelativeDate(c.lastModified)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
