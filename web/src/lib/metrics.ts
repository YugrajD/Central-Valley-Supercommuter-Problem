// Metric definitions for the choropleth. Sequential ramp = magnitude (dataviz
// method); the diverging pair is reserved for scenario diff deltas (Stage 3).

export type MetricKey =
  | "need"
  | "jobs_60min"
  | "supercommuter_share"
  | "long_commute_share"
  | "median_income"
  | "median_rent"
  | "renter_share"
  | "transit_share"
  | "wfh_share";

export interface MetricDef {
  key: MetricKey;
  label: string;
  format: (v: number) => string;
  description: string;
}

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const usd = (v: number) => `$${Math.round(v).toLocaleString()}`;
const num = (v: number) => Math.round(v).toLocaleString();

export const METRICS: MetricDef[] = [
  {
    key: "need",
    label: "Composite need",
    format: (v: number) => v.toFixed(2),
    description: "Weighted need index from the equity sliders (0 = least, 1 = most)",
  },
  {
    key: "jobs_60min",
    label: "Bay jobs in 60 min",
    format: num,
    description: "Jobs reachable by transit + walking within 60 minutes (the headline number)",
  },
  {
    key: "supercommuter_share",
    label: "Super-commuters",
    format: pct,
    description: "Share of workers commuting 90+ minutes each way (ACS B08303)",
  },
  {
    key: "long_commute_share",
    label: "60+ min commutes",
    format: pct,
    description: "Share of workers commuting 60 minutes or more",
  },
  {
    key: "median_income",
    label: "Median income",
    format: usd,
    description: "Median household income (ACS B19013)",
  },
  {
    key: "median_rent",
    label: "Median rent",
    format: usd,
    description: "Median gross rent (ACS B25064)",
  },
  {
    key: "renter_share",
    label: "Renters",
    format: pct,
    description: "Share of renter-occupied households (ACS B25003)",
  },
  {
    key: "transit_share",
    label: "Transit riders",
    format: pct,
    description: "Share of workers commuting by public transit (ACS B08301)",
  },
  {
    key: "wfh_share",
    label: "Work from home",
    format: pct,
    description: "Share of workers working from home (ACS B08301)",
  },
];

// Validated sequential blue ramp (dataviz reference palette, steps 100→700)
export const SEQ_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"];

// Diverging pair for diffs: red (loss) ↔ gray ↔ blue (gain)
export const DIV_NEG = "#d03b3b";
export const DIV_MID_DARK = "#383835";
export const DIV_MID_LIGHT = "#f0efec";
export const DIV_POS = "#3987e5";
