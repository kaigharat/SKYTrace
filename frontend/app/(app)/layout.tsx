import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { api } from "@/lib/api";

export default async function AppGroupLayout({ children }: { children: ReactNode }) {
  const repositories = await api.getRepositories().catch(() => []);
  return <AppShell repositories={repositories}>{children}</AppShell>;
}
