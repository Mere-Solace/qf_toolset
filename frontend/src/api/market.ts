import client from "./client";
import type { Quote, HistoryResponse, FinancialsResponse } from "@/types";

export async function getQuote(ticker: string): Promise<Quote> {
  const { data } = await client.get<Quote>(`/market/quote/${ticker}`);
  return data;
}

export async function getHistory(
  ticker: string,
  params?: { period?: string; interval?: string }
): Promise<HistoryResponse> {
  const { data } = await client.get<HistoryResponse>(
    `/market/history/${ticker}`,
    { params }
  );
  return data;
}

export async function getFinancials(ticker: string): Promise<FinancialsResponse> {
  const { data } = await client.get<FinancialsResponse>(
    `/market/financials/${ticker}`
  );
  return data;
}

export async function exportFinancials(ticker: string): Promise<Blob> {
  const { data } = await client.post(
    `/market/financials/${ticker}/export`,
    null,
    { responseType: "blob" }
  );
  return data;
}
