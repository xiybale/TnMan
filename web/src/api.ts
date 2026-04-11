import type { BatchSummary, ComparePayload, MatchReport, PlayerDetail, PlayerSummary, Surface } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export const api = {
  players: async () => fetchJson<{ players: PlayerSummary[] }>("/players"),
  player: async (playerId: string) => fetchJson<PlayerDetail>(`/players/${playerId}`),
  compare: async (playerOne: string, playerTwo: string, surface: Surface) =>
    fetchJson<ComparePayload>(
      `/compare?player_one=${encodeURIComponent(playerOne)}&player_two=${encodeURIComponent(playerTwo)}&surface=${surface}`,
    ),
  simulateMatch: async (payload: {
    playerOne: string;
    playerTwo: string;
    surface: Surface;
    bestOfSets: number;
    seed: number;
  }) =>
    fetchJson<MatchReport>("/simulate/match", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  simulateBatch: async (payload: {
    playerOne: string;
    playerTwo: string;
    surface: Surface;
    bestOfSets: number;
    seed: number;
    iterations: number;
  }) =>
    fetchJson<BatchSummary>("/simulate/batch", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
