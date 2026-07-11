"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { aceLine, aceStations } from "@/data/placeholder";
import { METRICS, SEQ_RAMP, type MetricKey } from "@/lib/metrics";

const STYLES = {
  dark: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
  light: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
} as const;

export type Theme = keyof typeof STYLES;

export interface MapProps {
  theme?: Theme;
  metric: MetricKey;
  tracts: GeoJSON.FeatureCollection | null;
}

/** 5th–95th percentile span of a metric across tracts (robust to outliers). */
function metricSpan(tracts: GeoJSON.FeatureCollection, metric: MetricKey): [number, number] {
  const values = tracts.features
    .map((f) => f.properties?.[metric])
    .filter((v): v is number => typeof v === "number" && isFinite(v))
    .sort((a, b) => a - b);
  if (values.length === 0) return [0, 1];
  const q = (p: number) => values[Math.min(values.length - 1, Math.floor(p * values.length))];
  const lo = q(0.05);
  const hi = q(0.95);
  return hi > lo ? [lo, hi] : [lo, lo + 1];
}

function fillColor(span: [number, number], metric: MetricKey): maplibregl.ExpressionSpecification {
  const [lo, hi] = span;
  const stops = SEQ_RAMP.flatMap((color, i) => [
    lo + ((hi - lo) * i) / (SEQ_RAMP.length - 1),
    color,
  ]);
  return [
    "case",
    ["==", ["typeof", ["get", metric]], "number"],
    ["interpolate", ["linear"], ["get", metric], ...stops],
    "rgba(120,130,145,0.25)", // no data
  ] as unknown as maplibregl.ExpressionSpecification;
}

function addLayers(map: maplibregl.Map, tracts: GeoJSON.FeatureCollection | null, metric: MetricKey) {
  if (tracts && !map.getSource("tracts")) {
    map.addSource("tracts", { type: "geojson", data: tracts, promoteId: "geoid" });
    const span = metricSpan(tracts, metric);
    map.addLayer({
      id: "tracts-fill",
      type: "fill",
      source: "tracts",
      paint: {
        "fill-color": fillColor(span, metric),
        "fill-opacity": [
          "case",
          ["boolean", ["feature-state", "hover"], false],
          0.85,
          0.55,
        ],
      },
    });
    map.addLayer({
      id: "tracts-line",
      type: "line",
      source: "tracts",
      paint: { "line-color": "#8a97ab", "line-width": 0.4, "line-opacity": 0.4 },
    });
  }

  if (!map.getSource("ace-line")) {
    map.addSource("ace-line", { type: "geojson", data: aceLine });
    map.addSource("ace-stations", { type: "geojson", data: aceStations });
    map.addLayer({
      id: "ace-line",
      type: "line",
      source: "ace-line",
      paint: { "line-color": "#f59e0b", "line-width": 3, "line-opacity": 0.9 },
    });
    map.addLayer({
      id: "ace-stations",
      type: "circle",
      source: "ace-stations",
      paint: {
        "circle-radius": 4,
        "circle-color": "#0d1017",
        "circle-stroke-color": "#f59e0b",
        "circle-stroke-width": 2,
      },
    });
  }
}

function popupHtml(p: Record<string, unknown>, metric: MetricKey): string {
  const def = METRICS.find((m) => m.key === metric)!;
  const v = p[metric];
  const main =
    typeof v === "number" ? def.format(v) : "no data";
  const extra = METRICS.filter((m) => m.key !== metric && typeof p[m.key] === "number")
    .slice(0, 3)
    .map(
      (m) =>
        `<div><span style="color:#8a97ab">${m.label}:</span> ${m.format(p[m.key] as number)}</div>`,
    )
    .join("");
  return `<strong>${p.name ?? p.geoid}</strong>
    <div style="margin:4px 0"><span style="color:#8a97ab">${def.label}:</span> <strong>${main}</strong></div>
    ${extra}`;
}

export default function Map({ theme = "dark", metric, tracts }: MapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const loadedRef = useRef(false);

  // create once
  useEffect(() => {
    if (!containerRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLES.dark,
      center: [-121.4, 37.85],
      zoom: 9,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.on("load", () => {
      loadedRef.current = true;
    });
    mapRef.current = map;
    return () => {
      loadedRef.current = false;
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // (re)apply style on theme change, then re-add layers
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    map.setStyle(STYLES[theme]);
    map.once("styledata", () => addLayers(map, tracts, metric));
  }, [theme]); // eslint-disable-line react-hooks/exhaustive-deps

  // add layers when data arrives / map ready; update paint on metric change
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const apply = () => {
      addLayers(map, tracts, metric);
      if (tracts && map.getLayer("tracts-fill")) {
        map.setPaintProperty("tracts-fill", "fill-color", fillColor(metricSpan(tracts, metric), metric));
      }
    };
    if (loadedRef.current && map.isStyleLoaded()) apply();
    else map.once("load", apply);
  }, [tracts, metric]);

  // hover popup + highlight
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const popup = new maplibregl.Popup({ closeButton: false, offset: 8, maxWidth: "280px" });
    let hovered: string | number | undefined;

    const onMove = (e: maplibregl.MapLayerMouseEvent) => {
      const f = e.features?.[0];
      if (!f) return;
      map.getCanvas().style.cursor = "pointer";
      if (hovered !== undefined) {
        map.setFeatureState({ source: "tracts", id: hovered }, { hover: false });
      }
      hovered = f.id;
      if (hovered !== undefined) {
        map.setFeatureState({ source: "tracts", id: hovered }, { hover: true });
      }
      popup.setLngLat(e.lngLat).setHTML(popupHtml(f.properties ?? {}, metric)).addTo(map);
    };
    const onLeave = () => {
      map.getCanvas().style.cursor = "";
      if (hovered !== undefined) {
        map.setFeatureState({ source: "tracts", id: hovered }, { hover: false });
        hovered = undefined;
      }
      popup.remove();
    };
    map.on("mousemove", "tracts-fill", onMove);
    map.on("mouseleave", "tracts-fill", onLeave);
    return () => {
      map.off("mousemove", "tracts-fill", onMove);
      map.off("mouseleave", "tracts-fill", onLeave);
      popup.remove();
    };
  }, [metric, tracts]);

  return <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />;
}
