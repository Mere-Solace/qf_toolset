import client from "./client";
import type {
  OptionPricingInput,
  BinomialInput,
  MonteCarloInput,
  OptionPricingResult,
  ImpliedVolInput,
  ImpliedVolResult,
  GreeksSurfaceResponse,
} from "@/types";

export async function priceBlackScholes(
  input: OptionPricingInput
): Promise<OptionPricingResult> {
  const { data } = await client.post<OptionPricingResult>(
    "/options/black-scholes",
    input
  );
  return data;
}

export async function priceBinomial(
  input: BinomialInput
): Promise<OptionPricingResult> {
  const { data } = await client.post<OptionPricingResult>(
    "/options/binomial",
    input
  );
  return data;
}

export async function priceMonteCarlo(
  input: MonteCarloInput
): Promise<OptionPricingResult> {
  const { data } = await client.post<OptionPricingResult>(
    "/options/monte-carlo",
    input
  );
  return data;
}

export async function getImpliedVol(
  input: ImpliedVolInput
): Promise<ImpliedVolResult> {
  const { data } = await client.post<ImpliedVolResult>(
    "/options/implied-vol",
    input
  );
  return data;
}

export async function getGreeksSurface(
  ticker: string
): Promise<GreeksSurfaceResponse> {
  const { data } = await client.get<GreeksSurfaceResponse>(
    "/options/greeks-surface",
    { params: { ticker } }
  );
  return data;
}
