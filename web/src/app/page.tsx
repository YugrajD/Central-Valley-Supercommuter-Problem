"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import type { Theme } from "@/components/Map";
import { METRICS, SEQ_RAMP, type MetricKey } from "@/lib/metrics";

// MapLibre touches window — client-only.
const Map = dynamic(() => import("@/components/Map"), { ssr: false });

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [theme, setTheme] = useState<Theme>("dark");
  const [metric, setMetric] = useState<MetricKey>("supercommuter_share");
  const [tracts, setTracts] = useState<GeoJSON.FeatureCollection | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/baseline`)
      .then((r) => {
        if (!r.ok) throw new Error(`API ${r.status}`);
        return r.json();
      })
      .then(setTracts)
      .catch((e) => setError(String(e)));
  }, []);

  const hasJobs = useMemo(
    () => tracts?.features.some((f) => typeof f.properties?.jobs_60min === "number") ?? false,
    [tracts],
  );
  const available = METRICS.filter((m) => m.key !== "jobs_60min" || hasJobs);
  const active = METRICS.find((m) => m.key === metric)!;

  return (
    <main>
      <Map theme={theme} metric={metric} tracts={tracts} />

      <div className="panel" style={{ top: 16, left: 16, padding: "14px 16px", maxWidth: 330 }}>
        <h1 style={{ margin: 0, fontSize: 18, letterSpacing: "0.04em" }}>ALTAMONT</h1>
        <p style={{ margin: "6px 0 0", fontSize: 12.5, lineHeight: 1.45, color: "var(--muted)" }}>
          {tracts
            ? `${tracts.features.length} San Joaquin County tracts. ${active.description}.`
            : error
              ? `API unreachable (${error}) — start it with: uvicorn api.main:app`
              : "Loading tracts…"}
        </p>

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
        {!hasJobs && (
          <p style={{ margin: "8px 0 0", fontSize: 11, color: "var(--rail)" }}>
            Baseline accessibility not computed yet — equity layers only.
          </p>
        )}
      </div>

      <div className="panel" style={{ top: 16, right: 16, padding: 8, display: "flex", gap: 6 }}>
        {(["light", "dark"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTheme(t)}
            style={{
              background: theme === t ? "#263145" : "#1a2130",
              color: "var(--ink)",
              border: `1px solid ${theme === t ? "#3a4a66" : "var(--line)"}`,
              borderRadius: 8,
              padding: "7px 11px",
              fontSize: 12,
              cursor: "pointer",
              textTransform: "capitalize",
            }}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="panel" style={{ bottom: 16, left: 16, padding: "12px 14px", fontSize: 12 }}>
        <div style={{ marginBottom: 6 }}>{active.label}</div>
        <div
          style={{
            width: 180,
            height: 10,
            borderRadius: 5,
            background: `linear-gradient(to right, ${SEQ_RAMP.join(",")})`,
          }}
        />
        <div style={{ display: "flex", justifyContent: "space-between", color: "var(--muted)", marginTop: 3, fontSize: 10.5 }}>
          <span>low</span>
          <span>high</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 9, marginTop: 10 }}>
          <span style={{ width: 16, height: 3, borderRadius: 2, background: "var(--rail)", flex: "none" }} />
          ACE rail corridor
        </div>
      </div>
    </main>
  );
}
