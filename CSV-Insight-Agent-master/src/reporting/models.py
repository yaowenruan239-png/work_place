from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReportMetric:
    label: str
    value: str
    description: str = ""


@dataclass
class ReportFinding:
    title: str
    detail: str
    category: str = "核心发现"


@dataclass
class ChartNarrative:
    title: str
    image_path: str | None
    chart_type: str
    why_it_matters: str
    observation: str
    recommendation: str


@dataclass
class ReportDocument:
    title: str
    subtitle: str
    query: str
    summary: str
    metrics: list[ReportMetric] = field(default_factory=list)
    findings: list[ReportFinding] = field(default_factory=list)
    chart_narratives: list[ChartNarrative] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    appendix: dict[str, Any] = field(default_factory=dict)
