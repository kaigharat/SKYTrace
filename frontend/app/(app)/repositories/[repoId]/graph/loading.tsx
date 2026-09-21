import { Skeleton } from "@/components/ui/skeleton";

export default function GraphLoading() {
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-4" aria-busy="true" aria-live="polite">
      <Skeleton className="h-7 w-72" />
      <Skeleton className="h-[560px] w-full rounded-xl" />
    </div>
  );
}
