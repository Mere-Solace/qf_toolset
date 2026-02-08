import Plot from "react-plotly.js";
import { darkLayout, defaultConfig } from "./plotlyDefaults";

interface OptionsPayoffProps {
  S: number;
  K: number;
  premium: number;
  optionType: "call" | "put";
  height?: number;
}

export default function OptionsPayoff({
  S,
  K,
  premium,
  optionType,
  height = 380,
}: OptionsPayoffProps) {
  const low = Math.floor(K * 0.6);
  const high = Math.ceil(K * 1.4);
  const step = (high - low) / 200;

  const prices: number[] = [];
  const payoff: number[] = [];
  const profit: number[] = [];
  const zeros: number[] = [];

  for (let p = low; p <= high; p += step) {
    prices.push(p);
    const intrinsic =
      optionType === "call" ? Math.max(p - K, 0) : Math.max(K - p, 0);
    payoff.push(intrinsic);
    profit.push(intrinsic - premium);
    zeros.push(0);
  }

  return (
    <Plot
      data={[
        {
          x: prices,
          y: payoff,
          type: "scatter",
          mode: "lines",
          name: "Payoff",
          line: { color: "#60a5fa", width: 2, dash: "dash" },
        },
        {
          x: prices,
          y: profit,
          type: "scatter",
          mode: "lines",
          name: "Profit / Loss",
          line: { color: "#22c55e", width: 2.5 },
          fill: "tozeroy",
          fillcolor: "rgba(34,197,94,0.08)",
        },
        {
          x: prices,
          y: zeros,
          type: "scatter",
          mode: "lines",
          name: "",
          line: { color: "#475569", width: 1, dash: "dot" },
          showlegend: false,
        },
        {
          x: [S],
          y: [0],
          type: "scatter",
          name: "Spot",
          marker: { size: 10, color: "#f59e0b", symbol: "diamond" },
          text: [`S=${S.toFixed(1)}`],
          textposition: "top center",
          textfont: { color: "#f59e0b" },
        },
      ]}
      layout={{
        ...darkLayout,
        title: {
          text: `${optionType === "call" ? "Call" : "Put"} Option Payoff (K=${K})`,
          font: { color: "#e2e8f0", size: 14 },
        },
        xaxis: { ...darkLayout.xaxis, title: { text: "Underlying Price" } },
        yaxis: { ...darkLayout.yaxis, title: { text: "P&L" } },
        height,
        autosize: true,
        showlegend: true,
        legend: { ...darkLayout.legend, x: 0.02, y: 0.98 },
      }}
      config={defaultConfig}
      useResizeHandler
      style={{ width: "100%" }}
    />
  );
}
