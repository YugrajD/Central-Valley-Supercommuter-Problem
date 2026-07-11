"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import type { Theme } from "@/components/Map";
import ScenarioPanel from "@/components/ScenarioPanel";
import DiffPanel from "@/components/DiffPanel";
import EquitySliders from "@/components/EquitySliders";
import {
  fetchBaseline,
  fetchScenarioDiff,
  fetchScenarios,
  type ScenarioDiff,
  type ScenarioInfo,
} from "@/lib/api";
import { DEFAULT_WEIGHTS, withNeed, type Weights } from "@/lib/equity";
import { DIV_MID_DARK, DIV_NEG, DIV_POS, METRICS, SEQ_RAMP, type MetricKey } from "@/lib/metrics";

// MapLibre touches window — client-only.
const Map = dynamic(() => import("@/components/Map"), { ssr: false });

const CUTOFF_MIN = 60;

export default function Home() {
  const [theme, setTheme] = useState<Theme>("dark");
  const [metric, setMetric] = useState<MetricKey>("supercommuter_share");
  const [tracts, setTracts] = useState<GeoJSON.FeatureCollection | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  const [activeScenario, setActiveScenario] = useState<string | null>(null);
  const [loadingScenario, setLoadingScenario] = useState<string | null>(null);
  const [scenarioError, setScenarioError] = useState<string | null>(null);
  const [diff, setDiff] = useState<ScenarioDiff | null>(null);

  const [weights, setWeights] = useState<Weights>(DEFAULT_WEIGHTS);
  const [equityOn, setEquityOn] = useState(false);

  useEffect(() => {
    fetchBaseline().then(setTracts).catch((e) => setError(String(e)));
    fetchScenarios().then(setScenarios).catch(() => setScenarios([]));
  }, []);

  const onToggleScenario = (id: string | null) => {
    setScenarioError(null);
    if (id === null) {
      setActiveScenario(null);
      setDiff(null);
      return;
    }
    setLoadingScenario(id);
    fetchScenarioDiff(id, CUTOFF_MIN)
      .then((d) => {
        // diff geojson lacks equity columns; graft them from baseline by geoid
        const equityByGeoid = new window.Map<string, Record<string, unknown>>(
          (tracts?.features ?? []).map((f) => [String(f.properties?.geoid), f.properties ?? {}]),
        );
        const geojson: GeoJSON.FeatureCollection = {
          ...d.geojson,
          features: d.geojson.features.map((f) => ({
            ...f,
            properties: {
              ...equityByGeoid.get(String(f.properties?.geoid)),
              ...f.properties,
            },
          })),
        };
        setDiff({ ...d, geojson });
        setActiveScenario(id);
      })
      .catch((e) => setScenarioError(String(e.message ?? e)))
      .finally(() => setLoadingScenario(null));
  };

  const hasJobs = useMemo(
    () => tracts?.features.some((f) => typeof f.properties?.jobs_60min === "number") ?? false,
    [tracts],
  );

  // equity weighting is client-side arithmetic over loaded GeoJSON — live, no API call
  const displayTracts = useMemo(
    () => (tracts && equityOn ? withNeed(tracts, weights) : tracts),
    [tracts, equityOn, weights],
  );
  const displayDiff = useMemo(
    () => (diff ? (equityOn ? withNeed(diff.geojson, weights) : diff.geojson) : null),
    [diff, equityOn, weights],
  );

  const weightedGainers = useMemo(() => {
    if (!equityOn || !displayDiff) return null;
    return displayDiff.features
      .map((f) => ({
        geoid: String(f.properties?.geoid),
        delta: Number(f.properties?.delta ?? 0),
        weighted: Number(f.properties?.weighted_delta ?? 0),
      }))
      .filter((g) => g.weighted > 0)
      .sort((a, b) => b.weighted - a.weighted)
      .slice(0, 5);
  }, [equityOn, displayDiff]);

  const mapMetric: MetricKey = equityOn && !diff ? "need" : metric;
  const available = METRICS.filter(
    (m) => m.key !== "need" && (m.key !== "jobs_60min" || hasJobs),
  );
  const active = METRICS.find((m) => m.key === mapMetric)!;
  const activeScenarioInfo = scenarios.find((s) => s.id === activeScenario);

  return (
    <main>
      <Map theme={theme} metric={mapMetric} tracts={displayTracts} diff={displayDiff && diff ? displayDiff : null} />

      <div className="panel" style={{ top: 16, left: 16, padding: "14px 16px", maxWidth: 330 }}>
        <h1 style={{ margin: 0, fontSize: 18, letterSpacing: "0.04em" }}>ALTAMONT</h1>
        <p style={{ margin: "6px 0 0", fontSize: 12.5, lineHeight: 1.45, color: "var(--muted)" }}>
          {diff
            ? `Change in Bay Area jobs reachable within ${CUTOFF_MIN} minutes by transit, per tract.`
            : tracts
              ? `${tracts.features.length} San Joaquin County tracts. ${active.description}.`
              : error
                ? `API unreachable (${error}) — start it with: uvicorn api.main:app`
                : "Loading tracts…"}
        </p>

        {!diff && !equityOn && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginTop: 10 }}>
            {available.map((m) => (
              <button
                key={m.key}
                onClick={() => setMetric(m.key)}
                style={{
                  background: metric === m.key ? "#263145" : "#1a2130",
                  color: "var(--ink)",
                  border: `1px solid ${metric === m.key ? "#3a4a66" : "var(--line)"}`,
                  borderRadius: 7,
                  padding: "5px 9px",
                  fontSize: 11.5,
                  cursor: "pointer",
                }}
              >
                {m.label}
              </button>
            ))}
          </div>
        )}
        {!hasJobs && !diff && (
          <p style={{ margin: "8px 0 0", fontSize: 11, color: "var(--rail)" }}>
            Baseline accessibility not computed yet — equity layers only.
          </p>
        )}
      </div>

      <ScenarioPanel
        scenarios={scenarios}
        active={activeScenario}
        loading={loadingScenario}
        error={scenarioError}
        onToggle={onToggleScenario}
      />

      <EquitySliders
        weights={weights}
        enabled={equityOn}
        onChange={setWeights}
        onToggle={setEquityOn}
      />

      {diff && activeScenarioInfo && (
        <DiffPanel
          headline={diff.headline}
          scenarioName={activeScenarioInfo.name}
          cutoffMin={CUTOFF_MIN}
          weightedGainers={weightedGainers}
        />
      )}

      <div className="panel" style={{ bottom: 16, left: 16, padding: "12px 14px", fontSize: 12 }}>
        <div style={{ marginBottom: 6 }}>{diff ? "Δ jobs reachable" : active.label}</div>
        <div
          style={{
            width: 180,
            height: 10,
            borderRadius: 5,
            background: diff
              ? `linear-gradient(to right, ${DIV_NEG}, ${DIV_MID_DARK}, ${DIV_POS})`
              : `linear-gradient(to right, ${SEQ_RAMP.join(",")})`,
          }}
        />
        <div style={{ display: "flex", justifyContent: "space-between", color: "var(--muted)", marginTop: 3, fontSize: 10.5 }}>
          <span>{diff ? "loss" : "low"}</span>
          {diff && <span>0</span>}
          <span>{diff ? "gain" : "high"}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 9, marginTop: 10 }}>
          <span style={{ width: 16, height: 3, borderRadius: 2, background: "var(--rail)", flex: "none" }} />
          ACE rail corridor
        </div>
        <div style={{ marginTop: 8, fontSize: 10.5, color: "var(--muted)", maxWidth: 200 }}>
          Fixed departure: weekday 6:30–7:30 AM. Access walk or park-and-ride;
          egress walk. R5 routing.
        </div>
      </div>

      <div className="panel" style={{ bottom: 16, left: "50%", transform: "translateX(-50%)", padding: 6, display: "flex", gap: 6 }}>
        {(["light", "dark"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTheme(t)}
            style={{
              background: theme === t ? "#263145" : "transparent",
              color: "var(--ink)",
              border: "1px solid var(--line)",
              borderRadius: 7,
              padding: "5px 10px",
              fontSize: 11.5,
              cursor: "pointer",
              textTransform: "capitalize",
            }}
          >
            {t}
          </button>
        ))}
      </div>
    </main>
  );
}
