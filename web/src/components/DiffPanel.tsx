"use client";

import type { DiffHeadline } from "@/lib/api";

export interface WeightedGainer {
  geoid: string;
  delta: number;
  weighted: number;
}

export default function DiffPanel({
  headline,
  scenarioName,
  cutoffMin,
  weightedGainers,
}: {
  headline: DiffHeadline;
  scenarioName: string;
  cutoffMin: number;
  weightedGainers?: WeightedGainer[] | null;
}) {
  const sign = headline.total_delta >= 0 ? "+" : "";
  return (
    <div
      className="panel"
      style={{ bottom: 16, right: 16, padding: "14px 16px", width: 280 }}
    >
      <div style={{ fontSize: 12, color: "var(--muted)" }}>{scenarioName}</div>
      <div style={{ fontSize: 26, fontWeight: 700, margin: "4px 0" }}>
        {sign}
        {headline.total_delta.toLocaleString()}
      </div>
      <div style={{ fontSize: 11.5, color: "var(--muted)", marginBottom: 8 }}>
        tract-jobs within {cutoffMin} min, summed across tracts
      </div>
      <div style={{ fontSize: 12 }}>
        <span style={{ color: "#3987e5", fontWeight: 600 }}>
          {headline.tracts_improved}
        </span>{" "}
        tracts gain
        {headline.tracts_worsened > 0 && (
          <>
            {" · "}
            <span style={{ color: "#d03b3b", fontWeight: 600 }}>
              {headline.tracts_worsened}
            </span>{" "}
            lose
          </>
        )}
      </div>
      {weightedGainers ? (
        <div style={{ marginTop: 8, fontSize: 11.5 }}>
          <div style={{ color: "var(--muted)", marginBottom: 4 }}>
            Biggest gains, weighted by need
          </div>
          {weightedGainers.map((g) => (
            <div
              key={g.geoid}
              style={{ display: "flex", justifyContent: "space-between", padding: "2px 0" }}
            >
              <span style={{ color: "var(--muted)" }}>tract {g.geoid.slice(-6)}</span>
              <span style={{ fontVariantNumeric: "tabular-nums" }}>
                +{g.delta.toLocaleString()}
              </span>
            </div>
          ))}
          {weightedGainers.length === 0 && (
            <div style={{ color: "var(--muted)" }}>
              no gains land on high-need tracts under these weights
            </div>
          )}
        </div>
      ) : (
        headline.top_gainers.length > 0 && (
          <div style={{ marginTop: 8, fontSize: 11.5 }}>
            <div style={{ color: "var(--muted)", marginBottom: 4 }}>Biggest gains</div>
            {headline.top_gainers.map((g) => (
              <div
                key={g.geoid}
                style={{ display: "flex", justifyContent: "space-between", padding: "2px 0" }}
              >
                <span style={{ color: "var(--muted)" }}>tract {g.geoid.slice(-6)}</span>
                <span style={{ fontVariantNumeric: "tabular-nums" }}>
                  +{g.delta.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );
}
