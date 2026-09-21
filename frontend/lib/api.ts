/**
 * SkyTrace API Client
 * Connects the Next.js frontend to the FastAPI backend.
 */

import type {
  AnalysisJob,
  CommitEntry,
  ComponentRisk,
  PullRequestReview,
  Repository,
  RepositoryGraph,
  RepositoryHealth,
  SecurityFinding,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window === "undefined" ? "http://127.0.0.1:8000" : "http://localhost:8000");

interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

async function apiFetch<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = 8000, ...fetchOptions } = options;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  const url = `${API_BASE_URL}${cleanEndpoint}`;

  try {
    const res = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...fetchOptions.headers,
      },
      cache: "no-store",
    });

    if (!res.ok) {
      const errorText = await res.text().catch(() => "");
      throw new Error(`API error ${res.status} (${res.statusText}): ${errorText}`);
    }

    return (await res.json()) as T;
  } finally {
    clearTimeout(timeoutId);
  }
}

export const api = {
  async checkHealth(): Promise<{ status: string; service: string; ml_ready: boolean }> {
    return apiFetch("/health");
  },

  async getRepositories(): Promise<Repository[]> {
    return apiFetch<Repository[]>("/api/repositories");
  },

  async getRepository(id: string): Promise<Repository> {
    return apiFetch<Repository>(`/api/repositories/${id}`);
  },

  async getRepositoryHealth(id: string): Promise<RepositoryHealth> {
    return apiFetch<RepositoryHealth>(`/api/repositories/${id}/health`);
  },

  async getComponents(repositoryId: string): Promise<ComponentRisk[]> {
    return apiFetch<ComponentRisk[]>(`/api/repositories/${repositoryId}/components`);
  },

  async getComponent(repositoryId: string, componentId: string): Promise<ComponentRisk> {
    return apiFetch<ComponentRisk>(`/api/repositories/${repositoryId}/components/${componentId}`);
  },

  async getComponentCode(repositoryId: string, componentId: string): Promise<string> {
    const data = await apiFetch<{ componentId: string; code: string }>(
      `/api/repositories/${repositoryId}/components/${componentId}/code`,
    );
    return data.code;
  },

  async getComponentHistory(repositoryId: string, componentId: string): Promise<CommitEntry[]> {
    return apiFetch<CommitEntry[]>(
      `/api/repositories/${repositoryId}/components/${componentId}/history`,
    );
  },

  async getRepositoryGraph(repositoryId: string): Promise<RepositoryGraph> {
    return apiFetch<RepositoryGraph>(`/api/repositories/${repositoryId}/graph`);
  },

  async getSecurityFindings(repositoryId: string): Promise<SecurityFinding[]> {
    return apiFetch<SecurityFinding[]>(`/api/repositories/${repositoryId}/security`);
  },

  async getPullRequests(repositoryId: string): Promise<PullRequestReview[]> {
    return apiFetch<PullRequestReview[]>(`/api/repositories/${repositoryId}/pull-requests`);
  },

  async getPullRequest(prId: string): Promise<PullRequestReview> {
    return apiFetch<PullRequestReview>(`/api/pull-requests/${prId}`);
  },

  async connectRepository(payload: { fullName: string; description?: string }): Promise<Repository> {
    return apiFetch<Repository>("/api/repositories/connect", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async analyzeRepository(repositoryId: string): Promise<AnalysisJob> {
    return apiFetch<AnalysisJob>(`/api/repositories/${repositoryId}/analyze`, {
      method: "POST",
    });
  },

  /**
   * Real-time ML Prediction flow:
   * Sends code directly to FastAPI ML Inference Engine.
   */
  async predictCode(params: {
    code: string;
    path?: string;
    language?: string;
    repositoryId?: string;
    componentId?: string;
  }): Promise<{
    component: ComponentRisk;
    inferenceSource: string;
    status: string;
  }> {
    return apiFetch("/api/predict/code", {
      method: "POST",
      body: JSON.stringify({
        code: params.code,
        path: params.path || "source.py",
        language: params.language || "Python",
        repositoryId: params.repositoryId || "repo-orbit-payments",
        componentId: params.componentId,
      }),
    });
  },
};
