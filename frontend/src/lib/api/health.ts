export type ApiAvailability = "checking" | "connected" | "database-unavailable" | "unavailable";

type HealthPayload = {
  status?: unknown;
  services?: {
    database?: unknown;
  };
};

const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "") ??
  "http://localhost:8000/api/v1";

export async function checkApiHealth(signal: AbortSignal): Promise<ApiAvailability> {
  const response = await fetch(`${apiBaseUrl}/health`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });

  let payload: HealthPayload;
  try {
    payload = (await response.json()) as HealthPayload;
  } catch {
    return response.ok ? "unavailable" : "database-unavailable";
  }

  if (
    payload.status === "ok" &&
    payload.services?.database === "connected" &&
    response.ok
  ) {
    return "connected";
  }

  if (payload.status === "degraded" || payload.services?.database === "unavailable") {
    return "database-unavailable";
  }

  return "unavailable";
}
