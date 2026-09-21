import { notFound } from "next/navigation";
import { DependencyGraph } from "@/components/graph/dependency-graph";
import { getRepository, repositoryGraphs } from "@/lib/mock-data";
import { api } from "@/lib/api";

export default async function RepositoryGraphPage({
  params,
  searchParams,
}: {
  params: Promise<{ repoId: string }>;
  searchParams: Promise<{ focus?: string }>;
}) {
  const { repoId } = await params;
  const { focus } = await searchParams;

  let repo = await api.getRepository(repoId).catch(() => getRepository(repoId));
  if (!repo) repo = getRepository(repoId);

  let graph = await api.getRepositoryGraph(repoId).catch(() => repositoryGraphs[repoId]);
  if (!graph) graph = repositoryGraphs[repoId];

  if (!repo || !graph) notFound();

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dependency &amp; call graph</h1>
        <p className="text-sm text-muted-foreground">
          {repo.fullName} · {graph.nodes.length} nodes · {graph.edges.length} relationships
        </p>
      </div>
      <DependencyGraph repositoryId={repoId} graph={graph} focusId={focus} />
    </div>
  );
}
