import { useQuery } from "@tanstack/react-query";
import {
  getIndicators,
  getRecessionRisk,
  getMultiSeries,
  getYieldCurve,
} from "../api/macro";
import MultiSeriesChart from "../components/charts/MultiSeriesChart";
import Plot from "react-plotly.js";
import { darkLayout, defaultConfig } from "../components/charts/plotlyDefaults";
import type {
  IndicatorSummary,
  RecessionRiskResponse,
  YieldCurveResponse,
} from "../types";

function IndicatorCard({ indicator }: { indicator: IndicatorSummary }) {
  const isPositive = indicator.change !== null && indicator.change > 0;
  const isNegative = indicator.change !== null && indicator.change < 0;

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
      <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">
        {indicator.name}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-xl font-bold text-slate-100">
          {indicator.value.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
        </span>
        <span className="text-xs text-slate-500">{indicator.unit}</span>
      </div>
      {indicator.change !== null && (
        <div
          className={`text-xs mt-1 font-medium ${
            isPositive
              ? "text-green-400"
              : isNegative
              ? "text-red-400"
              : "text-slate-500"
          }`}
        >
          {isPositive ? "+" : ""}
          {indicator.change.toFixed(3)}
        </div>
      )}
    </div>
  );
}

function RecessionGauge({ risk }: { risk: RecessionRiskResponse }) {
  const pct = (risk.score / risk.total_signals) * 100;
  const color =
    risk.score <= 2
      ? "#22c55e"
      : risk.score <= 4
      ? "#f59e0b"
      : risk.score <= 6
      ? "#f97316"
      : "#ef4444";
  const label =
    risk.score <= 2
      ? "Low"
      : risk.score <= 4
      ? "Moderate"
      : risk.score <= 6
      ? "Elevated"
      : "High";

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
      <h3 className="text-sm font-semibold text-slate-300 mb-3">
        Recession Risk Score
      </h3>
      <div className="flex items-center gap-4 mb-4">
        <div
          className="text-4xl font-bold"
          style={{ color }}
        >
          {risk.score}/{risk.total_signals}
        </div>
        <div>
          <div className="text-sm font-medium" style={{ color }}>
            {label}
          </div>
          <div className="text-xs text-slate-500">
            {risk.score} of {risk.total_signals} signals triggered
          </div>
        </div>
      </div>
      {/* Progress bar */}
      <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden mb-4">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      {/* Signal list */}
      <div className="space-y-1.5">
        {risk.signals.map((sig) => (
          <div
            key={sig.series_id}
            className="flex items-center gap-2 text-xs"
          >
            <span
              className={`w-2 h-2 rounded-full flex-shrink-0 ${
                sig.signal ? "bg-red-500" : "bg-green-500"
              }`}
            />
            <span className="text-slate-400 flex-1 truncate">{sig.name}</span>
            <span className="font-mono text-slate-300">
              {sig.value.toFixed(2)}
            </span>
            <span className="text-slate-600">{sig.threshold}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function YieldCurveSnapshot({ data }: { data: YieldCurveResponse }) {
  return (
    <Plot
      data={[
        {
          x: data.points.map((p) => p.maturity),
          y: data.points.map((p) => p.rate),
          type: "scatter",
          mode: "lines+markers",
          line: { color: "#3b82f6", width: 3 },
          marker: { size: 8, color: "#3b82f6" },
          fill: "tozeroy",
          fillcolor: "rgba(59,130,246,0.08)",
        },
      ]}
      layout={{
        ...darkLayout,
        title: {
          text: `Yield Curve (${data.date})`,
          font: { color: "#e2e8f0", size: 13 },
        },
        height: 280,
        autosize: true,
        yaxis: { ...darkLayout.yaxis, title: { text: "%" } },
        margin: { l: 50, r: 20, t: 40, b: 40 },
      }}
      config={defaultConfig}
      useResizeHandler
      style={{ width: "100%" }}
    />
  );
}

export default function Dashboard() {
  const { data: indicators } = useQuery({
    queryKey: ["indicators"],
    queryFn: getIndicators,
  });

  const { data: recessionRisk } = useQuery({
    queryKey: ["recession-risk"],
    queryFn: getRecessionRisk,
  });

  const { data: yieldCurve } = useQuery({
    queryKey: ["yield-curve"],
    queryFn: () => getYieldCurve(),
  });

  // Auto-load key dashboard charts via queries (cached + auto-retry)
  const { data: spreadsData } = useQuery({
    queryKey: ["multi-series", "spreads"],
    queryFn: () =>
      getMultiSeries({
        series_ids: ["T10Y2Y", "T10Y3M", "FEDFUNDS"],
        start: "2000-01-01",
      }),
  });

  const { data: creditData } = useQuery({
    queryKey: ["multi-series", "credit"],
    queryFn: () =>
      getMultiSeries({
        series_ids: ["BAMLH0A0HYM2", "BAMLC0A0CM", "BAMLC0A4CBBB"],
        start: "2000-01-01",
      }),
  });

  const { data: leadingData } = useQuery({
    queryKey: ["multi-series", "leading"],
    queryFn: () =>
      getMultiSeries({
        series_ids: ["MANEMP", "UMCSENT", "NFCI", "ICSA", "T10Y2Y"],
        start: "2000-01-01",
        normalize: true,
      }),
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-100">
          Macro Dashboard
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Key economic indicators, spreads, and recession risk assessment
        </p>
      </div>

      {/* Indicator cards */}
      {indicators && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {indicators.map((ind) => (
            <IndicatorCard key={ind.name} indicator={ind} />
          ))}
        </div>
      )}

      {/* Top row: Yield curve + Recession risk */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
          {yieldCurve ? (
            <YieldCurveSnapshot data={yieldCurve} />
          ) : (
            <div className="h-64 flex items-center justify-center text-slate-600 text-sm">
              Loading yield curve...
            </div>
          )}
        </div>
        {recessionRisk ? (
          <RecessionGauge risk={recessionRisk} />
        ) : (
          <div className="bg-slate-900 rounded-lg border border-slate-800 p-4 h-64 flex items-center justify-center text-slate-600 text-sm">
            Loading recession risk...
          </div>
        )}
      </div>

      {/* Yield curve spreads chart */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
        <h3 className="text-sm font-semibold text-slate-300 mb-2">
          Yield Curve Spreads & Fed Funds
        </h3>
        {spreadsData ? (
          <MultiSeriesChart
            dates={spreadsData.dates}
            series={spreadsData.series}
            height={380}
            title=""
          />
        ) : (
          <div className="h-64 flex items-center justify-center text-slate-600 text-sm">
            Loading...
          </div>
        )}
      </div>

      {/* Bottom row: Credit spreads + Leading indicators */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
          <h3 className="text-sm font-semibold text-slate-300 mb-2">
            Credit Spreads (OAS)
          </h3>
          {creditData ? (
            <MultiSeriesChart
              dates={creditData.dates}
              series={creditData.series}
              height={350}
            />
          ) : (
            <div className="h-64 flex items-center justify-center text-slate-600 text-sm">
              Loading...
            </div>
          )}
        </div>

        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
          <h3 className="text-sm font-semibold text-slate-300 mb-2">
            Leading Indicators (Z-Score)
          </h3>
          {leadingData ? (
            <MultiSeriesChart
              dates={leadingData.dates}
              series={leadingData.series}
              height={350}
              normalized
            />
          ) : (
            <div className="h-64 flex items-center justify-center text-slate-600 text-sm">
              Loading...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
