import client from "./client";
import type {
  MacroSeriesResponse,
  YieldCurveResponse,
  SeriesCatalogEntry,
  MultiSeriesRequest,
  MultiSeriesResponse,
  CorrelationRequest,
  CorrelationResponse,
  RecessionRiskResponse,
  IndicatorSummary,
} from "@/types";

export async function getSeries(
  seriesId: string,
  params?: { start_date?: string; end_date?: string }
): Promise<MacroSeriesResponse> {
  const { data } = await client.get<MacroSeriesResponse>(
    `/macro/series/${seriesId}`,
    { params }
  );
  return data;
}

export async function getYieldCurve(
  date?: string
): Promise<YieldCurveResponse> {
  const { data } = await client.get<YieldCurveResponse>("/macro/yield-curve", {
    params: date ? { date } : undefined,
  });
  return data;
}

export async function getIndicators(): Promise<IndicatorSummary[]> {
  const { data } = await client.get<IndicatorSummary[]>("/macro/indicators");
  return data;
}

export async function getCatalog(): Promise<SeriesCatalogEntry[]> {
  const { data } = await client.get<SeriesCatalogEntry[]>("/macro/catalog");
  return data;
}

export async function getMultiSeries(
  body: MultiSeriesRequest
): Promise<MultiSeriesResponse> {
  const { data } = await client.post<MultiSeriesResponse>(
    "/macro/multi-series",
    body
  );
  return data;
}

export async function getCorrelation(
  body: CorrelationRequest
): Promise<CorrelationResponse> {
  const { data } = await client.post<CorrelationResponse>(
    "/macro/correlation",
    body
  );
  return data;
}

export async function getRecessionRisk(): Promise<RecessionRiskResponse> {
  const { data } = await client.get<RecessionRiskResponse>(
    "/macro/recession-risk"
  );
  return data;
}
