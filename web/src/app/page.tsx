"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import type { Theme } from "@/components/Map";
import ScenarioPanel from "@/components/ScenarioPanel";
import DiffPanel from "@/components/DiffPanel";
import {
  fetchBaseline,
  fetchScenarioDiff,
  fetchScenarios,
  type ScenarioDiff,
  type ScenarioInfo,
} from "@/lib/api";
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
        setDiff(d);
        setActiveScenario(id);
      })
      .catch((e) => setScenarioError(String(e.message ?? e)))
      .finally(() => setLoadingScenario(null));
  };

  const hasJobs = useMemo(
    () => tracts?.features.some((f) => typeof f.properties?.jobs_60min === "number") ?? false,
    [tracts],
  );
  const available = METRICS.filter((m) => m.key !== "jobs_60min" || hasJobs);
  const active = METRICS.find((m) => m.key === metric)!;
  const activeScenarioInfo = scenarios.find((s) => s.id === activeScenario);

  return (
    <main>
      <Map theme={theme} metric={metric} tracts={tracts} diff={diff?.geojson ?? null} />

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

        {!diff && (
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

      {diff && activeScenarioInfo && (
        <DiffPanel
          headline={diff.headline}
          scenarioName={activeScenarioInfo.name}
          cutoffMin={CUTOFF_MIN}
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
          Fixed departure: weekday 6:30–7:30 AM. Transit + walk, R5 routing.
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
