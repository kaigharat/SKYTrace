"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Boxes,
  GitPullRequest,
  LayoutDashboard,
  Menu,
  ShieldCheck,
} from "lucide-react";
import { LogoMark } from "@/components/shared/logo-mark";
import { RepoSwitcher } from "@/components/layout/repo-switcher";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import type { Repository } from "@/lib/types";

function useActiveRepoId(pathname: string) {
  const match = pathname.match(/^\/repositories\/([^/]+)/);
  return match ? match[1] : undefined;
}

function navItems(repoId?: string) {
  if (!repoId) return [];
  return [
    { href: `/repositories/${repoId}`, label: "Overview", icon: LayoutDashboard, exact: true },
    { href: `/repositories/${repoId}/graph`, label: "Dependency Graph", icon: Boxes },
    { href: `/repositories/${repoId}/pull-requests`, label: "Pull Requests", icon: GitPullRequest },
  ];
}

function SidebarContent({
  repositories,
  activeRepoId,
  pathname,
}: {
  repositories: Repository[];
  activeRepoId?: string;
  pathname: string;
}) {
  const items = navItems(activeRepoId);
  return (
    <div className="flex h-full flex-col gap-4 bg-sidebar text-sidebar-foreground">
      <div className="flex items-center gap-2 px-4 pt-5">
        <LogoMark />
        <span className="font-mono text-sm font-semibold tracking-tight">
          Repo Intelligence AI
        </span>
      </div>

      <div className="px-3">
        <RepoSwitcher repositories={repositories} activeRepoId={activeRepoId} />
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 px-3">
        {items.length === 0 && (
          <Link
            href="/repositories"
            className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-foreground"
          >
            <LayoutDashboard className="size-4" />
            All repositories
          </Link>
        )}
        {items.map((item) => {
          const active = item.exact
            ? pathname === item.href
            : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-foreground font-medium"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
              )}
              aria-current={active ? "page" : undefined}
            >
              <item.icon className="size-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-sidebar-border px-3 py-3">
        <div className="flex items-center gap-2 rounded-md px-2 py-1.5 text-xs text-sidebar-foreground/60">
          <ShieldCheck className="size-3.5" />
          Security scans powered by Semgrep + ML
        </div>
      </div>
    </div>
  );
}

export function AppShell({
  repositories,
  children,
}: {
  repositories: Repository[];
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const activeRepoId = useActiveRepoId(pathname);
  const [mobileOpen, setMobileOpen] = React.useState(false);

  return (
    <div className="flex min-h-svh w-full">
      <aside className="hidden w-64 shrink-0 border-r border-sidebar-border lg:block">
        <div className="sticky top-0 h-svh">
          <SidebarContent
            repositories={repositories}
            activeRepoId={activeRepoId}
            pathname={pathname}
          />
        </div>
      </aside>

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-72 p-0">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <SidebarContent
            repositories={repositories}
            activeRepoId={activeRepoId}
            pathname={pathname}
          />
        </SheetContent>
      </Sheet>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex h-14 items-center justify-between gap-3 border-b border-border bg-background/85 px-4 backdrop-blur">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            aria-label="Open navigation"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="size-5" />
          </Button>
          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Avatar className="size-8">
              <AvatarFallback className="bg-primary/15 text-xs font-medium text-primary">
                YR
              </AvatarFallback>
            </Avatar>
          </div>
        </header>
        <main className="flex-1 px-4 py-6 md:px-8 md:py-8">{children}</main>
      </div>
    </div>
  );
}
