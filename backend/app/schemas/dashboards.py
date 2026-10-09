from pydantic import BaseModel, Field


class MetricCount(BaseModel):
    label: str
    value: float | int
    unit: str | None = None


class AlertItem(BaseModel):
    severity: str
    module: str
    message: str


class ModuleDashboard(BaseModel):
    module: str
    title: str
    metrics: list[MetricCount]
    alerts: list[AlertItem] = Field(default_factory=list)


class ExecutiveDashboard(BaseModel):
    title: str = "AI-RMMS Executive Dashboard"
    metrics: list[MetricCount]
    alerts: list[AlertItem]
    modules: list[str]
