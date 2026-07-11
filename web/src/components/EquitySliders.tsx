"use client";

import { EQUITY_LAYERS, type EquityKey, type Weights } from "@/lib/equity";

export interface EquitySlidersProps {
  weights: Weights;
  enabled: boolean;
  onChange: (w: Weights) => void;
  onToggle: (enabled: boolean) => void;
}

export default function EquitySliders({
  weights,
  enabled,
  onChange,
  onToggle,
}: EquitySlidersProps) {
  return (
    <div className="panel" style={{ top: 16, right: 312, padding: "12px 14px", width: 230 }}>
      <label
        style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13,
                 fontWeight: 600, cursor: "pointer" }}
      >
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onToggle(e.target.checked)}
        />
        Weight by need
      </label>
      <div style={{ fontSize: 10.5, color: "var(--muted)", margin: "4px 0 8px" }}>
        Who should count most? These weights are yours, not ours.
      </div>
      {enabled &&
        EQUITY_LAYERS.map((layer) => (
          <div key={layer.key} style={{ marginBottom: 7 }}>
            <div
              style={{ display: "flex", justifyContent: "space-between", fontSize: 11.5 }}
            >
              <span>{layer.label}</span>
              <span style={{ color: "var(--muted)", fontVariantNumeric: "tabular-nums" }}>
                {weights[layer.key]}
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              value={weights[layer.key]}
              onChange={(e) =>
                onChange({ ...weights, [layer.key]: Number(e.target.value) } as Weights)
              }
              style={{ width: "100%", accentColor: "#3987e5" }}
            />
          </div>
        ))}
    </div>
  );
}
