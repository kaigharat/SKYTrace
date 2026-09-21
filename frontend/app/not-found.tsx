import Link from "next/link";
import { FileSearch } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LogoMark } from "@/components/shared/logo-mark";

export default function NotFound() {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-6 px-4">
      <Link href="/" className="flex items-center gap-2">
        <LogoMark />
        <span className="font-mono text-sm font-semibold">Repository Intelligence AI</span>
      </Link>
      <Card className="w-full max-w-sm items-center gap-3 p-8 text-center">
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
