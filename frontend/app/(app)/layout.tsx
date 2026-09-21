import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { repositories } from "@/lib/mock-data";

export default function AppGroupLayout({ children }: { children: ReactNode }) {
  return <AppShell repositories={repositories}>{children}</AppShell>;
}
