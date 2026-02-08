import { useState, useMemo } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { getCatalog, getMultiSeries, getCorrelation } from "../api/macro";
import MultiSeriesChart from "../components/charts/MultiSeriesChart";
import CorrelationHeatmap from "../components/charts/CorrelationHeatmap";
import type {
  SeriesCatalogEntry,
  MultiSeriesResponse,
  CorrelationResponse,
} from "../types";

const CATEGORY_LABELS: Record<string, string> = {
  rates: "Treasury Rates",
  spreads: "Spreads & Credit",
  inflation: "Inflation",
  employment: "Employment",
  leading: "Leading Indicators",
  monetary: "Monetary Policy",
  conditions: "Financial Conditions",
  output: "Output & Activity",
  recession: "Recession Signals",
};

const PRESET_VIEWS: Record<string, { label: string; ids: string[]; normalize?: boolean }> = {
  yield_curve_spreads: {
    label: "Yield Curve Spreads",
    ids: ["T10Y2Y", "T10Y3M", "T10YFF"],
  },
  credit_spreads: {
    label: "Credit Spreads",
    ids: ["BAMLH0A0HYM2", "BAMLC0A0CM", "BAMLC0A4CBBB", "BAMLH0A1HYBB"],
  },
  rates_vs_fed: {
    label: "Rates vs Fed Funds",
    ids: ["DGS2", "DGS10", "DGS30", "FEDFUNDS"],
  },
  inflation_expectations: {
    label: "Inflation Expectations",
    ids: ["T10YIE", "T5YIE", "T5YIFR", "MICH"],
  },
  leading_composite: {
    label: "Leading Indicators (Normalized)",
    ids: ["NAPM", "UMCSENT", "PERMIT", "ICSA", "USSLIND"],
    normalize: true,
  },
  financial_stress: {
    label: "Financial Stress",
    ids: ["NFCI", "STLFSI4", "VIXCLS"],
    normalize: true,
  },
  labor_market: {
    label: "Labor Market",
    ids: ["UNRATE", "PAYEMS", "ICSA", "CIVPART"],
    normalize: true,
  },
  recession_watch: {
    label: "Recession Watch",
    ids: ["RECPROUSM156N", "SAHMREALTIME", "CFNAI", "T10Y3M"],
    normalize: true,
  },
};

export default function MacroIndicators() {
  const [selectedIds, setSelectedIds] = useState<string[]>(["T10Y2Y", "T10Y3M"]);
  const [normalize, setNormalize] = useState(false);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [activeTab, setActiveTab] = useState<"chart" | "correlation">("chart");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");

  // Fetch series catalog
  const { data: catalog, isLoading: catalogLoading } = useQuery({
    queryKey: ["macro-catalog"],
    queryFn: getCatalog,
  });

  // Fetch multi-series data
  const multiSeriesMutation = useMutation({
    mutationFn: getMultiSeries,
  });

  // Fetch correlation data
  const correlationMutation = useMutation({
    mutationFn: getCorrelation,
  });

  // Grouped catalog by category
  const groupedCatalog = useMemo(() => {
    if (!catalog) return {};
    const groups: Record<string, SeriesCatalogEntry[]> = {};
    for (const entry of catalog) {
      const cat = entry.category || "other";
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(entry);
    }
    return groups;
  }, [catalog]);

  const filteredCatalog = useMemo(() => {
    if (!catalog) return [];
    if (categoryFilter === "all") return catalog;
    return catalog.filter((e) => e.category === categoryFilter);
  }, [catalog, categoryFilter]);

  const toggleSeries = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  const applyPreset = (key: string) => {
    const preset = PRESET_VIEWS[key];
    if (preset) {
      setSelectedIds(preset.ids);
      setNormalize(preset.normalize ?? false);
    }
  };

  const fetchData = () => {
    if (selectedIds.length === 0) return;

    const body = {
      series_ids: selectedIds,
      ...(startDate ? { start: startDate } : {}),
      ...(endDate ? { end: endDate } : {}),
      normalize,
    };

    multiSeriesMutation.mutate(body);

    if (selectedIds.length >= 2 && activeTab === "correlation") {
      correlationMutation.mutate({
        series_ids: selectedIds,
        ...(startDate ? { start: startDate } : {}),
        ...(endDate ? { end: endDate } : {}),
      });
    }
  };

  const fetchCorrelation = () => {
    if (selectedIds.length < 2) return;
    correlationMutation.mutate({
      series_ids: selectedIds,
      ...(startDate ? { start: startDate } : {}),
      ...(endDate ? { end: endDate } : {}),
    });
  };

  const msData: MultiSeriesResponse | undefined = multiSeriesMutation.data;
  const corrData: CorrelationResponse | undefined = correlationMutation.data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Macro Indicators</h1>
        <p className="text-sm text-slate-400 mt-1">
          Select multiple FRED series to compare, correlate, and analyze
        </p>
      </div>

      {/* Preset views */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
          Quick Views
        </h3>
        <div className="flex flex-wrap gap-2">
          {Object.entries(PRESET_VIEWS).map(([key, preset]) => (
            <button
              key={key}
              onClick={() => applyPreset(key)}
              className="px-3 py-1.5 text-xs rounded-md bg-slate-800 text-slate-300 hover:bg-blue-600/20 hover:text-blue-400 transition-colors border border-slate-700"
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Left: Series selector */}
        <div className="col-span-4 bg-slate-900 rounded-lg border border-slate-800 p-4 max-h-[600px] overflow-y-auto">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-300">
              Series ({selectedIds.length} selected)
            </h3>
            {selectedIds.length > 0 && (
              <button
                onClick={() => setSelectedIds([])}
                className="text-xs text-slate-500 hover:text-red-400"
              >
                Clear all
              </button>
            )}
          </div>

          {/* Category filter */}
          <div className="mb-3">
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full text-xs bg-slate-800 border border-slate-700 text-slate-300 rounded px-2 py-1.5"
            >
              <option value="all">All Categories</option>
              {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          {catalogLoading ? (
            <p className="text-xs text-slate-500">Loading catalog...</p>
          ) : (
            <div className="space-y-1">
              {filteredCatalog.map((entry) => (
                <label
                  key={entry.series_id}
                  className={`flex items-center gap-2 px-2 py-1.5 rounded text-xs cursor-pointer transition-colors ${
                    selectedIds.includes(entry.series_id)
                      ? "bg-blue-600/20 text-blue-300"
                      : "text-slate-400 hover:bg-slate-800"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(entry.series_id)}
                    onChange={() => toggleSeries(entry.series_id)}
                    className="rounded border-slate-600 bg-slate-800 text-blue-500 focus:ring-blue-500"
                  />
                  <span className="flex-1 truncate">{entry.display_name}</span>
                  <span className="text-slate-600 flex-shrink-0">
                    {entry.series_id}
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Right: Controls + Chart area */}
        <div className="col-span-8 space-y-4">
          {/* Controls */}
          <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
            <div className="flex flex-wrap items-end gap-4">
              <div>
                <label className="block text-xs text-slate-500 mb-1">Start</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="bg-slate-800 border border-slate-700 text-slate-300 text-xs rounded px-2 py-1.5"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">End</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="bg-slate-800 border border-slate-700 text-slate-300 text-xs rounded px-2 py-1.5"
                />
              </div>
              <label className="flex items-center gap-2 text-xs text-slate-400">
                <input
                  type="checkbox"
                  checked={normalize}
                  onChange={(e) => setNormalize(e.target.checked)}
                  className="rounded border-slate-600 bg-slate-800 text-blue-500"
                />
                Z-Score Normalize
              </label>
              <button
                onClick={fetchData}
                disabled={
                  selectedIds.length === 0 || multiSeriesMutation.isPending
                }
                className="px-4 py-1.5 bg-blue-600 text-white text-xs font-medium rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {multiSeriesMutation.isPending ? "Loading..." : "Load Data"}
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 bg-slate-900 rounded-lg border border-slate-800 p-1">
            <button
              onClick={() => setActiveTab("chart")}
              className={`flex-1 py-1.5 text-xs font-medium rounded transition-colors ${
                activeTab === "chart"
                  ? "bg-blue-600 text-white"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Time Series Chart
            </button>
            <button
              onClick={() => {
                setActiveTab("correlation");
                if (selectedIds.length >= 2 && !corrData) fetchCorrelation();
              }}
              className={`flex-1 py-1.5 text-xs font-medium rounded transition-colors ${
                activeTab === "correlation"
                  ? "bg-blue-600 text-white"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Correlation Analysis
            </button>
          </div>

          {/* Chart / Correlation content */}
          {activeTab === "chart" && (
            <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
              {multiSeriesMutation.isPending && (
                <div className="flex items-center justify-center h-64 text-slate-500">
                  Loading series data...
                </div>
              )}
              {multiSeriesMutation.isError && (
                <div className="flex items-center justify-center h-64 text-red-400 text-sm">
                  {multiSeriesMutation.error.message}
                </div>
              )}
              {msData && (
                <MultiSeriesChart
                  dates={msData.dates}
                  series={msData.series}
                  normalized={normalize}
                  title={
                    normalize
                      ? "Z-Score Normalized Comparison"
                      : "Multi-Series Comparison"
                  }
                  height={500}
                />
              )}
              {!msData && !multiSeriesMutation.isPending && (
                <div className="flex items-center justify-center h-64 text-slate-600 text-sm">
                  Select series and click "Load Data" to visualize
                </div>
              )}
            </div>
          )}

          {activeTab === "correlation" && (
            <div className="space-y-4">
              <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
                {correlationMutation.isPending && (
                  <div className="flex items-center justify-center h-64 text-slate-500">
                    Computing correlations...
                  </div>
                )}
                {correlationMutation.isError && (
                  <div className="flex items-center justify-center h-64 text-red-400 text-sm">
                    {correlationMutation.error.message}
                  </div>
                )}
                {corrData && (
                  <CorrelationHeatmap
                    data={corrData.contemporaneous}
                    title="Contemporaneous Correlation"
                  />
                )}
                {selectedIds.length < 2 && (
                  <div className="flex items-center justify-center h-64 text-slate-600 text-sm">
                    Select at least 2 series for correlation analysis
                  </div>
                )}
              </div>

              {/* Lagged correlation table */}
              {corrData && corrData.lagged.length > 0 && (
                <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
                  <h3 className="text-sm font-semibold text-slate-300 mb-3">
                    Optimal Lag Analysis
                  </h3>
                  <p className="text-xs text-slate-500 mb-3">
                    Positive lag = Series A leads Series B by N months
                  </p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-slate-700">
                          <th className="text-left py-2 px-3 text-slate-400">
                            Series A
                          </th>
                          <th className="text-left py-2 px-3 text-slate-400">
                            Series B
                          </th>
                          <th className="text-right py-2 px-3 text-slate-400">
                            Correlation
                          </th>
                          <th className="text-right py-2 px-3 text-slate-400">
                            Optimal Lag
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {corrData.lagged.map((pair, i) => (
                          <tr
                            key={i}
                            className="border-b border-slate-800 hover:bg-slate-800/50"
                          >
                            <td className="py-2 px-3 text-slate-300">
                              {pair.series_a}
                            </td>
                            <td className="py-2 px-3 text-slate-300">
                              {pair.series_b}
                            </td>
                            <td
                              className={`py-2 px-3 text-right font-mono ${
                                pair.correlation > 0
                                  ? "text-green-400"
                                  : "text-red-400"
                              }`}
                            >
                              {pair.correlation.toFixed(4)}
                            </td>
                            <td className="py-2 px-3 text-right font-mono text-slate-300">
                              {pair.optimal_lag > 0
                                ? `+${pair.optimal_lag}mo`
                                : pair.optimal_lag < 0
                                ? `${pair.optimal_lag}mo`
                                : "0 (sync)"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
