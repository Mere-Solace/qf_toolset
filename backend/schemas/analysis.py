"""Pydantic schemas for statistical-analysis endpoints."""

from pydantic import BaseModel


class RegressionCoefficient(BaseModel):
    """A single coefficient from a regression model."""

    variable: str
    coefficient: float
    p_value: float
    significance: str


class RegressionResult(BaseModel):
    """Summary output of a regression model."""

    model_name: str
    r_squared: float
    adj_r_squared: float
    coefficients: list[RegressionCoefficient]
    vif: dict[str, float]


class VARResult(BaseModel):
    """Summary output of a Vector Auto-Regression model."""

    lag_order: int
    is_stable: bool
    forecast: list[dict]


class RunAnalysisRequest(BaseModel):
    """Optional parameters for triggering an analysis run."""

    csv_path: str | None = None
