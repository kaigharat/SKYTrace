import Link from "next/link";
import { FileSearch } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function RepositoryNotFound() {
  return (
    <div className="mx-auto flex max-w-sm flex-col items-center gap-3 py-24 text-center">
      <Card className="w-full items-center gap-3 p-8">
        <FileSearch className="size-8 text-muted-foreground" aria-hidden="true" />
        <h1 className="text-lg font-semibold">Not found</h1>
        <p className="text-sm text-muted-foreground">
          This repository, component or page doesn&apos;t exist or hasn&apos;t been connected yet.
        </p>
        <Button asChild className="mt-2">
          <Link href="/repositories">Back to repositories</Link>
        </Button>
      </Card>
    </div>
  );
}
