"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import type { Theme } from "@/components/Map";

// MapLibre touches window — client-only.
const Map = dynamic(() => import("@/components/Map"), { ssr: false });

export default function Home() {
  const [theme, setTheme] = useState<Theme>("dark");

  return (
    <main>
      <Map theme={theme} />

      <div className="panel" style={{ top: 16, left: 16, padding: "14px 16px", maxWidth: 320 }}>
        <h1 style={{ margin: 0, fontSize: 18, letterSpacing: "0.04em" }}>ALTAMONT</h1>
        <p style={{ margin: "6px 0 0", fontSize: 12.5, lineHeight: 1.45, color: "var(--muted)" }}>
          San Joaquin County → Bay Area job access. Circles show where residents
          live (green) and where jobs are (blue). The amber line is the ACE rail
          corridor. <span style={{ color: "var(--rail)" }}>Placeholder data</span> —
          real LODES/ACS wiring is Stage 1–2.
        </p>
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

      <div className="panel" style={{ bottom: 16, left: 16, padding: "12px 14px", fontSize: 12.5 }}>
        {[
          ["var(--accent)", "Residents (SJ County)"],
          ["var(--jobs)", "Jobs (Bay Area)"],
        ].map(([color, label]) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: 9, margin: "6px 0" }}>
            <span style={{ width: 12, height: 12, borderRadius: "50%", background: color, flex: "none" }} />
            {label}
          </div>
        ))}
        <div style={{ display: "flex", alignItems: "center", gap: 9, margin: "6px 0" }}>
          <span style={{ width: 16, height: 3, borderRadius: 2, background: "var(--rail)", flex: "none" }} />
          ACE rail corridor
        </div>
        <div style={{ color: "var(--muted)", marginTop: 8, fontSize: 11.5 }}>
          Circle area ∝ population / jobs · hover for detail
        </div>
      </div>
    </main>
  );
}
