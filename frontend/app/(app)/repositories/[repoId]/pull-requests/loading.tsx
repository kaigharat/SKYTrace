import { Skeleton } from "@/components/ui/skeleton";

export default function PullRequestsLoading() {
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6" aria-busy="true" aria-live="polite">
      <Skeleton className="h-7 w-56" />
      <div className="flex flex-col gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-20 w-full rounded-lg" />
        ))}
      </div>
    </div>
  );
}
