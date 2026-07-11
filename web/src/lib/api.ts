const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ScenarioInfo {
  id: string;
  name: string;
  description: string;
  computed: boolean;
}

export interface DiffHeadline {
  total_delta: number;
  tracts_improved: number;
  tracts_worsened: number;
  top_gainers: { geoid: string; delta: number; baseline: number }[];
}

export interface ScenarioDiff {
  scenario_id: string;
  cutoff_min: number;
  headline: DiffHeadline;
  geojson: GeoJSON.FeatureCollection;
}

async function ok<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const body = await r.json().catch(() => null);
    throw new Error(body?.detail ?? `API ${r.status}`);
  }
  return r.json();
}

export const fetchBaseline = () =>
  fetch(`${API}/baseline`).then((r) => ok<GeoJSON.FeatureCollection>(r));

export const fetchScenarios = () =>
  fetch(`${API}/scenarios`).then((r) => ok<ScenarioInfo[]>(r));

export const fetchScenarioDiff = (scenarioId: string, cutoffMin = 60) =>
  fetch(`${API}/scenario`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario_id: scenarioId, cutoff_min: cutoffMin }),
  }).then((r) => ok<ScenarioDiff>(r));
