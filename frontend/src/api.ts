import { QueryResultEnvelope, QueryStatus } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

type CreateQueryPayload = {
  question: string;
  confidence_threshold: number;
  max_passes: number;
};

type CreateQueryResponse = {
  id: string;
  status: string;
  created_at: string;
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function createQuery(payload: CreateQueryPayload): Promise<CreateQueryResponse> {
  return request<CreateQueryResponse>("/query", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getQueryStatus(queryId: string): Promise<QueryStatus> {
  return request<QueryStatus>(`/query/${queryId}/status`);
}

export async function getQueryResult(queryId: string): Promise<QueryResultEnvelope> {
  return request<QueryResultEnvelope>(`/query/${queryId}/result`);
}

