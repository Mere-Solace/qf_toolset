import { useQuery } from "@tanstack/react-query";
import { getYieldCurve } from "../api/macro";
import Plot from "react-plotly.js";
import { darkLayout, defaultConfig } from "../components/charts/plotlyDefaults";

export default function YieldCurve() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["yield-curve"],
    queryFn: () => getYieldCurve(),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Yield Curve</h1>
        <p className="text-sm text-slate-400 mt-1">
          Treasury yield curve snapshot
        </p>
      </div>

      <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
        {isLoading && (
          <div className="h-96 flex items-center justify-center text-slate-500">
            Loading yield curve data...
          </div>
        )}
        {error && (
          <div className="h-96 flex items-center justify-center text-red-400 text-sm">
            Failed to load yield curve data. Ensure the FRED pipeline has been run.
          </div>
        )}
        {data && (
          <Plot
            data={[
              {
                x: data.points.map((p) => p.maturity),
                y: data.points.map((p) => p.rate),
                type: "scatter",
                mode: "lines+markers",
                line: { color: "#3b82f6", width: 3, shape: "spline" },
                marker: { size: 10, color: "#3b82f6" },
                fill: "tozeroy",
                fillcolor: "rgba(59,130,246,0.08)",
              },
            ]}
            layout={{
              ...darkLayout,
              title: {
                text: `US Treasury Yield Curve — ${data.date}`,
                font: { color: "#e2e8f0", size: 16 },
              },
              height: 500,
              autosize: true,
              yaxis: { ...darkLayout.yaxis, title: { text: "Yield (%)" } },
              xaxis: { ...darkLayout.xaxis, title: { text: "Maturity" } },
            }}
            config={defaultConfig}
            useResizeHandler
            style={{ width: "100%" }}
          />
        )}
      </div>
    </div>
  );
}
