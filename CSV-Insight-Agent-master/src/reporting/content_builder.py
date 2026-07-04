from __future__ import annotations

from typing import Any

from src.reporting.models import ChartNarrative, ReportDocument, ReportFinding, ReportMetric


class ReportContentBuilder:
    def build(
        self,
        profile: dict[str, Any] | None,
        charts: list[dict[str, Any]] | None,
        insights: list[str] | None,
        query: str | None,
    ) -> ReportDocument:
        profile = profile or {}
        charts = charts or []
        insights = insights or []
        query = query or "分析 CSV 数据"
        rows = profile.get("rows", 0)
        columns = profile.get("columns", 0)
        numeric_columns = profile.get("numeric_columns", []) or []
        categorical_columns = profile.get("categorical_columns", []) or []

        metrics = [
            ReportMetric("记录数", str(rows), "CSV 中参与分析的总行数"),
            ReportMetric("字段数", str(columns), "CSV 中参与分析的总列数"),
            ReportMetric("数值字段", str(len(numeric_columns)), "可用于趋势、分布和相关性分析"),
            ReportMetric("图表数", str(len(charts)), "本次生成并用于解释的图表数量"),
        ]
        findings = [
            ReportFinding(f"发现 {index}", insight)
            for index, insight in enumerate(insights[:6], start=1)
        ] or [ReportFinding("自动分析摘要", "当前报告基于数据画像和图表结果生成。")]
        chart_narratives = [
            ChartNarrative(
                title=str(chart.get("title") or f"图表 {index}"),
                image_path=chart.get("path"),
                chart_type=str(chart.get("chart_type") or "unknown"),
                why_it_matters=f"该图用于辅助理解 {chart.get('x_col') or '关键字段'} 与 {chart.get('y_col') or '指标'} 的关系。",
                observation=insights[(index - 1) % len(insights)] if insights else "该图展示了数据中的主要分布、对比或关联模式。",
                recommendation="结合业务背景进一步检查高值、低值、异常值和结构性差异。",
            )
            for index, chart in enumerate(charts, start=1)
        ]
        appendix = {
            "字段": ", ".join(profile.get("column_names", []) or []),
            "数值字段": ", ".join(numeric_columns) or "无",
            "类别字段": ", ".join(categorical_columns) or "无",
        }
        return ReportDocument(
            title="CSV 数据分析报告",
            subtitle="咨询式数据洞察报告",
            query=query,
            summary=f"本报告围绕“{query}”展开，基于 {rows} 行、{columns} 列数据生成画像、图表和行动建议。",
            metrics=metrics,
            findings=findings,
            chart_narratives=chart_narratives,
            recommendations=[
                "优先关注图表中呈现的高值、低值和异常波动。",
                "将数据发现与具体业务周期、区域或产品策略结合验证。",
                "对关键指标建立持续监控，避免只基于单次 CSV 快照做结论。",
            ],
            limitations=["本报告仅基于上传 CSV 的现有字段和记录生成，不代表外部事实。"],
            appendix=appendix,
        )
