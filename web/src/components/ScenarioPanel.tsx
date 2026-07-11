"use client";

import type { ScenarioInfo } from "@/lib/api";

export interface ScenarioPanelProps {
  scenarios: ScenarioInfo[];
  active: string | null;
  loading: string | null;
  error: string | null;
  onToggle: (id: string | null) => void;
}

export default function ScenarioPanel({
  scenarios,
  active,
  loading,
  error,
  onToggle,
}: ScenarioPanelProps) {
  if (scenarios.length === 0) return null;
  return (
    <div
      className="panel"
      style={{ top: 16, right: 16, padding: "12px 14px", width: 280 }}
    >
      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>What if…</div>
      {scenarios.map((s) => {
        const isActive = active === s.id;
        const isLoading = loading === s.id;
        return (
          <button
            key={s.id}
            onClick={() => onToggle(isActive ? null : s.id)}
            disabled={isLoading}
            title={s.description}
            style={{
              display: "block",
              width: "100%",
              textAlign: "left",
              background: isActive ? "#263145" : "#1a2130",
              color: "var(--ink)",
              border: `1px solid ${isActive ? "#3a4a66" : "var(--line)"}`,
              borderRadius: 8,
              padding: "8px 10px",
              fontSize: 12,
              cursor: isLoading ? "wait" : "pointer",
              marginBottom: 6,
              opacity: s.computed ? 1 : 0.6,
            }}
          >
            <div style={{ fontWeight: 600 }}>
              {isActive ? "✓ " : ""}
              {s.name}
              {isLoading ? " …" : ""}
            </div>
            <div style={{ color: "var(--muted)", fontSize: 11, marginTop: 2 }}>
              {s.computed ? s.description : "not precomputed yet"}
            </div>
          </button>
        );
      })}
      {error && (
        <div style={{ color: "#e66767", fontSize: 11.5, marginTop: 4 }}>{error}</div>
      )}
      {active && (
        <button
          onClick={() => onToggle(null)}
          style={{
            background: "transparent",
            color: "var(--muted)",
            border: "none",
            fontSize: 11.5,
            cursor: "pointer",
            padding: 0,
            marginTop: 2,
            textDecoration: "underline",
          }}
        >
          back to baseline
        </button>
      )}
    </div>
  );
}
