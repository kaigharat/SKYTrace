"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Boxes,
  Code2,
  GitPullRequest,
  HelpCircle,
  LayoutDashboard,
  Menu,
  ShieldCheck,
  ArrowDown,
  ExternalLink,
  Sparkles,
} from "lucide-react";
import { LogoMark } from "@/components/shared/logo-mark";
import { RepoSwitcher } from "@/components/layout/repo-switcher";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
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
    { href: `/repositories/${repoId}/components`, label: "Components", icon: Code2 },
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
      {/* App Title & Subtitle */}
      <div className="flex items-center gap-3 px-4 pt-5">
        <LogoMark />
        <div className="flex flex-col">
          <span className="font-mono text-sm font-bold tracking-tight text-sidebar-foreground">
            SkyTrace
          </span>
          <span className="text-[10px] font-medium text-sidebar-foreground/70">
            Repository Intelligence AI
          </span>
        </div>
      </div>

      <div className="px-3">
        <RepoSwitcher repositories={repositories} activeRepoId={activeRepoId} />
      </div>

      {/* Main Nav Items */}
      <nav className="flex flex-1 flex-col gap-1 px-3">
        {items.length === 0 && (
          <Link
            href="/onboarding"
            className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-foreground"
          >
            <LayoutDashboard className="size-4" />
            Connect a repository
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
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-foreground font-semibold shadow-xs"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
              )}
              aria-current={active ? "page" : undefined}
            >
              <item.icon className={cn("size-4", active ? "text-sidebar-primary" : "text-sidebar-foreground/60")} />
              <span>{item.label}</span>
            </Link>
          );
        })}

        {/* Small Info Card: How SkyTrace Works */}
        <div className="mt-4 rounded-lg border border-sidebar-border bg-sidebar-accent/30 p-3 text-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="font-mono font-bold text-[11px] text-sidebar-foreground">
              How SkyTrace works
            </span>
            <Sparkles className="size-3 text-sidebar-primary" />
          </div>
          <div className="flex flex-col gap-1 text-[11px] font-mono text-sidebar-foreground/80">
            <div className="bg-sidebar-accent/80 px-2 py-1 rounded border border-sidebar-border text-center">
              Source + Dependencies + History
            </div>
            <ArrowDown className="size-3 mx-auto text-sidebar-foreground/50" />
            <div className="bg-sidebar-accent/80 px-2 py-1 rounded border border-sidebar-border text-center">
              Feature Extraction
            </div>
            <ArrowDown className="size-3 mx-auto text-sidebar-foreground/50" />
            <div className="bg-sidebar-accent/80 px-2 py-1 rounded border border-sidebar-border text-center">
              ML Analysis
            </div>
            <ArrowDown className="size-3 mx-auto text-sidebar-foreground/50" />
            <div className="bg-sidebar-accent/80 px-2 py-1 rounded border border-sidebar-border text-center text-sidebar-primary font-bold">
              Risk + Evidence
            </div>
          </div>
          <Link
            href="/#workflow"
            className="mt-3 flex items-center gap-1 text-[10px] font-medium text-sidebar-primary hover:underline"
          >
            <HelpCircle className="size-3" />
            <span>View complete workflow guide</span>
          </Link>
        </div>
      </nav>

      {/* Footer Link */}
      <div className="border-t border-sidebar-border px-3 py-3">
        <Link
          href="/"
          className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-xs text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/50 transition-colors"
        >
          <div className="flex items-center gap-2">
            <ShieldCheck className="size-3.5 text-sidebar-primary" />
            <span>Homepage &amp; Workflow</span>
          </div>
          <ExternalLink className="size-3" />
        </Link>
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
    <div className="flex min-h-svh w-full bg-background">
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

          <div className="flex items-center gap-2">
            <Link href="/" className="font-mono text-xs font-bold hover:text-primary lg:hidden">
              SkyTrace
            </Link>
          </div>

          <div className="flex-1" />

          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" asChild className="text-xs">
              <Link href="/onboarding">Connect New Repo</Link>
            </Button>
            <ThemeToggle />
            <Avatar className="size-8 border border-border">
              <AvatarFallback className="bg-primary/15 text-xs font-bold text-primary">
                ST
              </AvatarFallback>
            </Avatar>
          </div>
        </header>

        <main className="flex-1 px-4 py-6 md:px-8 md:py-8">{children}</main>
      </div>
    </div>
  );
}
