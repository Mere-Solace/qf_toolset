import Plot from "react-plotly.js";
import { darkLayout, defaultConfig } from "./plotlyDefaults";
import type { CorrelationMatrix } from "@/types";

interface CorrelationHeatmapProps {
  data: CorrelationMatrix;
  title?: string;
  height?: number;
}

export default function CorrelationHeatmap({
  data,
  title = "Correlation Matrix",
  height = 500,
}: CorrelationHeatmapProps) {
  const trace: Plotly.Data = {
    z: data.matrix,
    x: data.display_names,
    y: data.display_names,
    type: "heatmap",
    colorscale: [
      [0, "#ef4444"],
      [0.5, "#1e293b"],
      [1, "#22c55e"],
    ],
    zmin: -1,
    zmax: 1,
    text: data.matrix.map((row) => row.map((v) => v.toFixed(3))),
    texttemplate: "%{text}",
    textfont: { color: "#e2e8f0", size: 10 },
    hovertemplate:
      "%{y} vs %{x}<br>Correlation: %{z:.4f}<extra></extra>",
    showscale: true,
    colorbar: {
      title: { text: "r", font: { color: "#94a3b8" } },
      tickfont: { color: "#94a3b8" },
    },
  };

  return (
    <Plot
      data={[trace]}
      layout={{
        ...darkLayout,
        title: { text: title, font: { color: "#e2e8f0", size: 14 } },
        height,
        autosize: true,
        xaxis: { ...darkLayout.xaxis, tickangle: -45 },
        yaxis: { ...darkLayout.yaxis, autorange: "reversed" as const },
        margin: { l: 140, r: 40, t: 50, b: 120 },
      }}
      config={defaultConfig}
      useResizeHandler
      style={{ width: "100%" }}
    />
  );
}
