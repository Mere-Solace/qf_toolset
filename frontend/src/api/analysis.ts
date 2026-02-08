import client from "./client";
import type {
  RegressionResult,
  VARResult,
  AnalysisRunRequest,
  VARRunRequest,
} from "@/types";

export async function getRegressionResults(): Promise<RegressionResult> {
  const { data } = await client.get<RegressionResult>(
    "/analysis/regression/results"
  );
  return data;
}

export async function getVARResults(): Promise<VARResult> {
  const { data } = await client.get<VARResult>("/analysis/var/results");
  return data;
}

export async function runRegression(
  request: AnalysisRunRequest
): Promise<RegressionResult> {
  const { data } = await client.post<RegressionResult>(
    "/analysis/regression/run",
    request
  );
  return data;
}

export async function runVAR(request: VARRunRequest): Promise<VARResult> {
  const { data } = await client.post<VARResult>("/analysis/var/run", request);
  return data;
}
