import Plot from "react-plotly.js";
import { darkLayout, defaultConfig } from "./plotlyDefaults";

interface TimeSeriesChartProps {
  dates: string[];
  values: number[];
  title?: string;
  yAxisLabel?: string;
  color?: string;
  height?: number;
}

export default function TimeSeriesChart({
  dates,
  values,
  title = "",
  yAxisLabel = "",
  color = "#3b82f6",
  height = 400,
}: TimeSeriesChartProps) {
  return (
    <Plot
      data={[
        {
          x: dates,
          y: values,
          type: "scatter",
          mode: "lines",
          line: { color, width: 2 },
          fill: "tozeroy",
          fillcolor: `${color}15`,
        },
      ]}
      layout={{
        ...darkLayout,
        title: { text: title, font: { color: "#e2e8f0", size: 14 } },
        yaxis: { ...darkLayout.yaxis, title: { text: yAxisLabel } },
        height,
        autosize: true,
      }}
      config={defaultConfig}
      useResizeHandler
      style={{ width: "100%" }}
    />
  );
}
