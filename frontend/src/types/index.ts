/* ── Market ── */

export interface Quote {
  ticker: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  market_cap?: number;
  timestamp: string;
}

export interface HistoryPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface HistoryResponse {
  ticker: string;
  data: HistoryPoint[];
}

export interface FinancialStatement {
  period: string;
  revenue?: number;
  net_income?: number;
  total_assets?: number;
  total_liabilities?: number;
  total_equity?: number;
  operating_cash_flow?: number;
  eps?: number;
  [key: string]: string | number | undefined;
}

export interface FinancialsResponse {
  ticker: string;
  income_statement: FinancialStatement[];
  balance_sheet: FinancialStatement[];
  cash_flow: FinancialStatement[];
}

/* ── Macro ── */

export interface MacroDataPoint {
  date: string;
  value: number;
}

export interface MacroSeriesResponse {
  series_id: string;
  title: string;
  data: MacroDataPoint[];
}

export interface YieldCurvePoint {
  maturity: string;
  rate: number;
}

export interface YieldCurveResponse {
  date: string;
  points: YieldCurvePoint[];
}

export interface MacroIndicator {
  id: string;
  name: string;
  source: string;
  latest_value: number;
  latest_date: string;
  unit: string;
}

/* ── Macro Catalog ── */

export interface SeriesCatalogEntry {
  series_id: string;
  display_name: string;
  unit: string;
  frequency: string;
  category: string;
  observation_count: number;
  first_date: string | null;
  last_date: string | null;
}

/* ── Multi-series ── */

export interface MultiSeriesRequest {
  series_ids: string[];
  start?: string;
  end?: string;
  normalize?: boolean;
}

export interface SeriesColumn {
  series_id: string;
  display_name: string;
  unit: string;
  values: (number | null)[];
}

export interface MultiSeriesResponse {
  dates: string[];
  series: SeriesColumn[];
}

/* ── Correlation ── */

export interface CorrelationRequest {
  series_ids: string[];
  start?: string;
  end?: string;
  max_lag?: number;
}

export interface CorrelationPair {
  series_a: string;
  series_b: string;
  correlation: number;
  optimal_lag: number;
}

export interface CorrelationMatrix {
  series_ids: string[];
  display_names: string[];
  matrix: number[][];
}

export interface CorrelationResponse {
  contemporaneous: CorrelationMatrix;
  lagged: CorrelationPair[];
}

/* ── Recession Risk ── */

export interface RecessionSignal {
  name: string;
  series_id: string;
  signal: boolean;
  value: number;
  threshold: string;
  description: string;
}

export interface RecessionRiskResponse {
  score: number;
  total_signals: number;
  signals: RecessionSignal[];
}

/* ── Indicator Summary ── */

export interface IndicatorSummary {
  name: string;
  value: number;
  change: number | null;
  unit: string;
}

/* ── Options ── */

export interface OptionPricingInput {
  S: number;
  K: number;
  T: number;
  r: number;
  sigma: number;
  option_type: "call" | "put";
}

export interface BinomialInput extends OptionPricingInput {
  steps: number;
}

export interface MonteCarloInput extends OptionPricingInput {
  simulations: number;
}

export interface OptionPricingResult {
  price: number;
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
  rho: number;
}

export interface ImpliedVolInput {
  S: number;
  K: number;
  T: number;
  r: number;
  market_price: number;
  option_type: "call" | "put";
}

export interface ImpliedVolResult {
  implied_vol: number;
}

export interface GreeksSurfacePoint {
  strike: number;
  expiry: number;
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
  rho: number;
}

export interface GreeksSurfaceResponse {
  ticker: string;
  data: GreeksSurfacePoint[];
}

/* ── Analysis ── */

export interface RegressionResult {
  dependent: string;
  independents: string[];
  coefficients: Record<string, number>;
  r_squared: number;
  adj_r_squared: number;
  p_values: Record<string, number>;
  residuals: number[];
}

export interface VARResult {
  variables: string[];
  lags: number;
  irf: Record<string, number[]>;
  forecast: Record<string, number[]>;
}

export interface AnalysisRunRequest {
  dependent: string;
  independents: string[];
  start_date?: string;
  end_date?: string;
}

export interface VARRunRequest {
  variables: string[];
  lags: number;
  start_date?: string;
  end_date?: string;
}

/* ── Data ── */

export interface DataSeries {
  id: string;
  name: string;
  source: string;
  frequency: string;
  last_updated: string;
}

/* ── WebSocket ── */

export interface PriceUpdate {
  ticker: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  timestamp: string;
}
