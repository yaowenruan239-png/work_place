from __future__ import annotations

from typing import Any

from src.skills.base import BaseSkill


class SuggestChartSkill(BaseSkill):
    name = "suggest_chart"
    description = "根据数据画像和用户问题推荐可执行图表计划。"
    args_schema = {"type": "object", "properties": {"profile": {"type": "object"}, "query": {"type": "string"}}, "required": ["profile"]}

    def run(self, **kwargs: Any) -> dict[str, Any]:
        profile = kwargs["profile"]
        numeric = profile.get("numeric_columns", [])
        categorical = profile.get("categorical_columns", [])
        recommendations: list[dict[str, Any]] = []

        if categorical and numeric:
            recommendations.append({"chart_type": "bar", "x_col": categorical[0], "y_col": numeric[0], "title": f"{categorical[0]} 与 {numeric[0]} 对比"})
            recommendations.append({"chart_type": "box", "x_col": categorical[0], "y_col": numeric[0], "title": f"不同 {categorical[0]} 的 {numeric[0]} 分布"})
        if len(numeric) >= 2:
            recommendations.append({"chart_type": "scatter", "x_col": numeric[0], "y_col": numeric[1], "title": f"{numeric[0]} 与 {numeric[1]} 关系"})
            recommendations.append({"chart_type": "correlation_heatmap", "title": "数值字段相关性热力图"})
        if numeric:
            recommendations.append({"chart_type": "histogram", "x_col": numeric[0], "title": f"{numeric[0]} 分布"})
        if categorical and not numeric:
            recommendations.append({"chart_type": "bar", "x_col": categorical[0], "title": f"{categorical[0]} 频次分布"})

        return {"success": bool(recommendations), "recommended": recommendations, "error": None if recommendations else "没有可推荐图表"}
