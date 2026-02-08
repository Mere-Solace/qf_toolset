import type { Layout as PlotlyLayout, Config } from "plotly.js";

export const darkLayout: Partial<PlotlyLayout> = {
  paper_bgcolor: "transparent",
  plot_bgcolor: "transparent",
  font: { color: "#cbd5e1", family: "Inter, system-ui, sans-serif" },
  xaxis: {
    gridcolor: "#1e293b",
    zerolinecolor: "#334155",
    tickfont: { color: "#94a3b8" },
  },
  yaxis: {
    gridcolor: "#1e293b",
    zerolinecolor: "#334155",
    tickfont: { color: "#94a3b8" },
  },
  margin: { l: 60, r: 20, t: 40, b: 40 },
  legend: { font: { color: "#94a3b8" } },
};

export const defaultConfig: Partial<Config> = {
  displayModeBar: true,
  displaylogo: false,
  responsive: true,
  modeBarButtonsToRemove: ["lasso2d", "select2d"],
};
