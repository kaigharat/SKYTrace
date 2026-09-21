import { Skeleton } from "@/components/ui/skeleton";
import { Card } from "@/components/ui/card";

export default function ComponentDetailLoading() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6" aria-busy="true" aria-live="polite">
      <Skeleton className="h-4 w-64" />
      <div className="flex items-start justify-between gap-4">
        <Skeleton className="h-7 w-72" />
        <Skeleton className="h-9 w-64" />
      </div>
      <Card className="p-5">
        <Skeleton className="h-16 w-full" />
      </Card>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="p-5 lg:col-span-2">
          <Skeleton className="h-48 w-full" />
        </Card>
        <Card className="p-5">
          <Skeleton className="h-48 w-full" />
        </Card>
      </div>
    </div>
  );
}
