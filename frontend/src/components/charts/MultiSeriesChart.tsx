import Plot from "react-plotly.js";
import { darkLayout, defaultConfig } from "./plotlyDefaults";
import type { SeriesColumn } from "@/types";

const COLORS = [
  "#3b82f6", "#ef4444", "#22c55e", "#f59e0b", "#8b5cf6",
  "#ec4899", "#06b6d4", "#f97316", "#14b8a6", "#a855f7",
  "#6366f1", "#10b981", "#e11d48", "#0ea5e9", "#84cc16",
];

interface MultiSeriesChartProps {
  dates: string[];
  series: SeriesColumn[];
  title?: string;
  height?: number;
  normalized?: boolean;
  showLegend?: boolean;
}

export default function MultiSeriesChart({
  dates,
  series,
  title = "",
  height = 500,
  normalized = false,
  showLegend = true,
}: MultiSeriesChartProps) {
  // Group by unit for dual-axis support (max 2 y-axes)
  const units = [...new Set(series.map((s) => s.unit))];
  const useSecondAxis = !normalized && units.length === 2;

  const traces: Plotly.Data[] = series.map((s, i) => {
    const yaxis = useSecondAxis && s.unit === units[1] ? "y2" : "y";
    return {
      x: dates,
      y: s.values,
      type: "scatter" as const,
      mode: "lines" as const,
      name: s.display_name,
      line: { color: COLORS[i % COLORS.length], width: 2 },
      yaxis,
      connectgaps: false,
      hovertemplate: `%{x}<br>${s.display_name}: %{y:.2f} ${s.unit}<extra></extra>`,
    };
  });

  const layout: Partial<Plotly.Layout> = {
    ...darkLayout,
    title: title ? { text: title, font: { color: "#e2e8f0", size: 14 } } : undefined,
    height,
    autosize: true,
    showlegend: showLegend,
    legend: {
      font: { color: "#94a3b8", size: 11 },
      bgcolor: "transparent",
      orientation: "h" as const,
      y: -0.15,
      x: 0.5,
      xanchor: "center" as const,
    },
    xaxis: {
      ...darkLayout.xaxis,
      type: "date",
      rangeslider: { visible: true, thickness: 0.06 },
      rangeselector: {
        buttons: [
          { count: 3, label: "3M", step: "month", stepmode: "backward" },
          { count: 1, label: "1Y", step: "year", stepmode: "backward" },
          { count: 5, label: "5Y", step: "year", stepmode: "backward" },
          { count: 10, label: "10Y", step: "year", stepmode: "backward" },
          { step: "all", label: "All" },
        ],
        font: { color: "#94a3b8", size: 10 },
        bgcolor: "#1e293b",
        activecolor: "#3b82f6",
      },
    },
    yaxis: {
      ...darkLayout.yaxis,
      title: normalized
        ? { text: "Z-Score" }
        : units.length > 0
        ? { text: units[0] }
        : undefined,
    },
    ...(useSecondAxis
      ? {
          yaxis2: {
            ...darkLayout.yaxis,
            title: { text: units[1] },
            overlaying: "y" as const,
            side: "right" as const,
          },
        }
      : {}),
    margin: { l: 60, r: useSecondAxis ? 60 : 20, t: 50, b: 40 },
    hovermode: "x unified" as const,
  };

  // Add zero line for Z-score charts
  if (normalized) {
    layout.shapes = [
      {
        type: "line",
        x0: 0,
        x1: 1,
        xref: "paper",
        y0: 0,
        y1: 0,
        yref: "y",
        line: { color: "#475569", width: 1, dash: "dash" },
      },
    ];
  }

  return (
    <Plot
      data={traces}
      layout={layout}
      config={defaultConfig}
      useResizeHandler
      style={{ width: "100%" }}
    />
  );
}
