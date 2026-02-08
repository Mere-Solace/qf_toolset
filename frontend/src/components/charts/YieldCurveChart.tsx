import Plot from "react-plotly.js";
import { darkLayout, defaultConfig } from "./plotlyDefaults";
import type { YieldCurvePoint } from "@/types";

interface YieldCurveChartProps {
  data: YieldCurvePoint[];
  date?: string;
  height?: number;
}

export default function YieldCurveChart({
  data,
  date,
  height = 450,
}: YieldCurveChartProps) {
  const maturities = data.map((p) => p.maturity);
  const rates = data.map((p) => p.rate);

  return (
    <Plot
      data={[
        {
          x: maturities,
          y: rates,
          type: "scatter",
          mode: "lines+markers",
          line: { color: "#3b82f6", width: 3, shape: "spline" },
          marker: { size: 8, color: "#60a5fa" },
          name: date ?? "Current",
        },
      ]}
      layout={{
        ...darkLayout,
        title: {
          text: `US Treasury Yield Curve${date ? ` (${date})` : ""}`,
          font: { color: "#e2e8f0", size: 16 },
        },
        xaxis: {
          ...darkLayout.xaxis,
          title: { text: "Maturity" },
        },
        yaxis: {
          ...darkLayout.yaxis,
          title: { text: "Yield (%)" },
          ticksuffix: "%",
        },
        height,
        autosize: true,
      }}
      config={defaultConfig}
      useResizeHandler
      style={{ width: "100%" }}
    />
  );
}
