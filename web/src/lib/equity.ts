// Client-side mirror of core/equity.py: weighted composite need per tract.
// Weights come from the sliders — never hardcoded (the whole point).

export const EQUITY_LAYERS = [
  { key: "supercommuter_share", label: "Super-commuters", direction: 1 },
  { key: "long_commute_share", label: "60+ min commutes", direction: 1 },
  { key: "renter_share", label: "Renters", direction: 1 },
  { key: "transit_share", label: "Transit riders", direction: 1 },
  { key: "median_income", label: "Low income", direction: -1 },
  { key: "median_rent", label: "Low rent", direction: -1 },
] as const;

export type EquityKey = (typeof EQUITY_LAYERS)[number]["key"];
export type Weights = Record<EquityKey, number>;

export const DEFAULT_WEIGHTS: Weights = {
  supercommuter_share: 50,
  long_commute_share: 0,
  renter_share: 0,
  transit_share: 0,
  median_income: 50,
  median_rent: 0,
};

/** Min-max normalize a layer across features; NaN/missing -> 0 (no signal). */
function normalized(features: GeoJSON.Feature[], key: EquityKey): number[] {
  const raw = features.map((f) => {
    const v = f.properties?.[key];
    return typeof v === "number" && isFinite(v) ? v : null;
  });
  const present = raw.filter((v): v is number => v !== null);
  const lo = Math.min(...present);
  const hi = Math.max(...present);
  if (present.length === 0 || hi === lo) return raw.map(() => 0);
  return raw.map((v) => (v === null ? 0 : (v - lo) / (hi - lo)));
}

/** Composite need in [0,1] per feature, aligned with the features array. */
export function needIndex(features: GeoJSON.Feature[], weights: Weights): number[] {
  const total = Object.values(weights).reduce((a, b) => a + b, 0);
  if (total <= 0) return features.map(() => 0);

  const acc = features.map(() => 0);
  for (const layer of EQUITY_LAYERS) {
    const w = weights[layer.key];
    if (w <= 0) continue;
    const norm = normalized(features, layer.key);
    for (let i = 0; i < acc.length; i++) {
      const v = layer.direction < 0 ? 1 - norm[i] : norm[i];
      acc[i] += (w / total) * v;
    }
  }
  return acc;
}

/** Clone a FeatureCollection with `need` (and `weighted_delta` if delta exists) props. */
export function withNeed(
  fc: GeoJSON.FeatureCollection,
  weights: Weights,
): GeoJSON.FeatureCollection {
  const need = needIndex(fc.features, weights);
  return {
    ...fc,
    features: fc.features.map((f, i) => ({
      ...f,
      properties: {
        ...f.properties,
        need: need[i],
        ...(typeof f.properties?.delta === "number"
          ? { weighted_delta: f.properties.delta * need[i] }
          : {}),
      },
    })),
  };
}
