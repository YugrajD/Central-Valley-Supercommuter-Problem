"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { residents, jobs, aceLine, aceStations } from "@/data/placeholder";

const STYLES = {
  dark: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
  light: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
} as const;

export type Theme = keyof typeof STYLES;

// radius: circle area proportional to value -> radius proportional to sqrt(value)
const radius = (max: number): maplibregl.ExpressionSpecification => [
  "interpolate",
  ["linear"],
  ["sqrt", ["get", "value"]],
  0,
  4,
  Math.sqrt(max),
  46,
];

function addDataLayers(map: maplibregl.Map) {
  map.addSource("residents", { type: "geojson", data: residents });
  map.addSource("jobs", { type: "geojson", data: jobs });
  map.addSource("ace-line", { type: "geojson", data: aceLine });
  map.addSource("ace-stations", { type: "geojson", data: aceStations });

  map.addLayer({
    id: "ace-line",
    type: "line",
    source: "ace-line",
    paint: {
      "line-color": "#f59e0b",
      "line-width": 3.5,
      "line-opacity": 0.85,
      "line-blur": 0.3,
    },
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

  map.addLayer({
    id: "residents",
    type: "circle",
    source: "residents",
    paint: {
      "circle-radius": radius(320000),
      "circle-color": "#34d399",
      "circle-opacity": 0.28,
      "circle-stroke-color": "#34d399",
      "circle-stroke-width": 1.4,
    },
  });
  map.addLayer({
    id: "jobs",
    type: "circle",
    source: "jobs",
    paint: {
      "circle-radius": radius(700000),
      "circle-color": "#60a5fa",
      "circle-opacity": 0.24,
      "circle-stroke-color": "#60a5fa",
      "circle-stroke-width": 1.4,
    },
  });

  map.addLayer({
    id: "labels",
    type: "symbol",
    source: "residents",
    layout: {
      "text-field": ["get", "name"],
      "text-size": 11,
      "text-offset": [0, 1.4],
      "text-anchor": "top",
    },
    paint: {
      "text-color": "#e8edf5",
      "text-halo-color": "#0d1017",
      "text-halo-width": 1.2,
    },
  });

  const popup = new maplibregl.Popup({ closeButton: false, offset: 10 });
  for (const id of ["residents", "jobs", "ace-stations"]) {
    map.on("mouseenter", id, (e) => {
      map.getCanvas().style.cursor = "pointer";
      const feature = e.features?.[0];
      if (!feature) return;
      const p = feature.properties as { name: string; kind: string; value?: number };
      const val = p.value
        ? `<br><span style="color:#8a97ab">${p.kind}:</span> ${Number(p.value).toLocaleString()}`
        : `<br><span style="color:#8a97ab">${p.kind}</span>`;
      popup.setLngLat(e.lngLat).setHTML(`<strong>${p.name}</strong>${val}`).addTo(map);
    });
    map.on("mouseleave", id, () => {
      map.getCanvas().style.cursor = "";
      popup.remove();
    });
  }
}

export default function Map({ theme = "dark" }: { theme?: Theme }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLES.dark,
      center: [-121.62, 37.72],
      zoom: 8.4,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.on("load", () => addDataLayers(map));
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    map.setStyle(STYLES[theme]);
    map.once("styledata", () => addDataLayers(map));
  }, [theme]);

  return <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />;
}
