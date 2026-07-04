from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from pandas.api.types import is_numeric_dtype

from src.skills.base import BaseSkill
from src.utils.chart_utils import setup_chinese_font

SUPPORTED_CHARTS = {"line", "bar", "scatter", "histogram", "box", "correlation_heatmap"}


class PlotChartSkill(BaseSkill):
    name = "plot_chart"
    description = "生成单张 PNG 图表，支持 line、bar、scatter、histogram、box、correlation_heatmap。"
    args_schema = {"type": "object", "properties": {"csv_path": {"type": "string"}, "chart_type": {"type": "string"}}, "required": ["csv_path", "chart_type"]}

    def __init__(self, output_dir: str | Path = "outputs/charts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, **kwargs: Any) -> dict[str, Any]:
        csv_path = Path(kwargs["csv_path"])
        chart_type = kwargs.get("chart_type", "bar")
        run_id = kwargs.get("run_id", datetime.now().strftime("%Y%m%d%H%M%S"))
        x_col = kwargs.get("x_col")
        y_col = kwargs.get("y_col")
        title = kwargs.get("title") or chart_type

        if chart_type not in SUPPORTED_CHARTS:
            return {"success": False, "error": f"不支持的图表类型: {chart_type}", "suggestion": sorted(SUPPORTED_CHARTS)}
        if not csv_path.exists():
            return {"success": False, "error": f"CSV 文件不存在: {csv_path}"}

        try:
            df = pd.read_csv(csv_path)
        except Exception as exc:
            return {"success": False, "error": f"CSV 读取失败: {exc}"}

        columns = list(df.columns)
        numeric = [column for column in columns if is_numeric_dtype(df[column])]
        validation_error = self._validate(chart_type, columns, numeric, x_col, y_col)
        if validation_error:
            return validation_error

        setup_chinese_font()
        fig, ax = plt.subplots(figsize=(10, 6))
        try:
            if chart_type == "line":
                data = df[[x_col, y_col]].dropna().sort_values(x_col)
                ax.plot(data[x_col], data[y_col], marker="o")
            elif chart_type == "scatter":
                data = df[[x_col, y_col]].dropna()
                if len(data) > 1000:
                    data = data.sample(1000, random_state=42)
                ax.scatter(data[x_col], data[y_col], alpha=0.7)
            elif chart_type == "bar":
                if y_col and y_col in numeric:
                    df.groupby(x_col)[y_col].mean().sort_values(ascending=False).head(15).plot(kind="bar", ax=ax)
                else:
                    df[x_col].dropna().astype(str).value_counts().head(15).iloc[::-1].plot(kind="barh", ax=ax)
            elif chart_type == "histogram":
                ax.hist(df[x_col].dropna(), bins=int(kwargs.get("bins", 30)), edgecolor="white")
            elif chart_type == "box":
                df[[x_col, y_col]].dropna().boxplot(column=y_col, by=x_col, ax=ax, rot=30)
                fig.suptitle("")
            elif chart_type == "correlation_heatmap":
                corr = df[numeric].corr(numeric_only=True)
                image = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
                ax.set_xticks(range(len(corr.columns)), corr.columns, rotation=45, ha="right")
                ax.set_yticks(range(len(corr.index)), corr.index)
                fig.colorbar(image, ax=ax)

            ax.set_title(title)
            if x_col:
                ax.set_xlabel(x_col)
            if y_col:
                ax.set_ylabel(y_col)
            fig.tight_layout()
            filename = f"{run_id}_{chart_type}_{datetime.now().strftime('%H%M%S%f')}.png"
            path = self.output_dir / filename
            fig.savefig(path, dpi=150, bbox_inches="tight")
            return {"success": True, "path": str(path), "chart_type": chart_type, "x_col": x_col, "y_col": y_col, "title": title}
        except Exception as exc:
            return {"success": False, "error": f"图表生成异常: {exc}"}
        finally:
            plt.close(fig)

    def _validate(self, chart_type: str, columns: list[str], numeric: list[str], x_col: str | None, y_col: str | None) -> dict[str, Any] | None:
        if chart_type == "correlation_heatmap":
            if len(numeric) < 2:
                return {"success": False, "error": "相关性热力图至少需要两个数值列", "suggestion": numeric}
            return None
        if chart_type in {"line", "scatter", "box"} and (not x_col or not y_col):
            return {"success": False, "error": f"{chart_type} 需要 x_col 和 y_col", "suggestion": columns}
        if chart_type in {"bar", "histogram"} and not x_col:
            return {"success": False, "error": f"{chart_type} 需要 x_col", "suggestion": columns}
        for column in [x_col, y_col]:
            if column and column not in columns:
                return {"success": False, "error": f"列不存在: {column}", "suggestion": columns}
        if chart_type in {"line", "scatter"} and y_col not in numeric:
            return {"success": False, "error": f"y_col 必须是数值列: {y_col}", "suggestion": numeric}
        if chart_type == "histogram" and x_col not in numeric:
            return {"success": False, "error": f"直方图字段必须是数值列: {x_col}", "suggestion": numeric}
        if chart_type == "box" and y_col not in numeric:
            return {"success": False, "error": f"箱线图 y_col 必须是数值列: {y_col}", "suggestion": numeric}
        return None


class PlotChartBatchSkill(BaseSkill):
    name = "plot_chart_batch"
    description = "批量生成多张 PNG 图表。"
    args_schema = {"type": "object", "properties": {"csv_path": {"type": "string"}, "plans": {"type": "array"}}, "required": ["csv_path", "plans"]}

    def __init__(self, output_dir: str | Path = "outputs/charts"):
        self.plotter = PlotChartSkill(output_dir=output_dir)

    def run(self, **kwargs: Any) -> dict[str, Any]:
        charts = []
        errors = []
        for index, plan in enumerate(kwargs.get("plans", []), start=1):
            result = self.plotter.run(csv_path=kwargs["csv_path"], run_id=kwargs.get("run_id", "run"), **plan)
            if result.get("success"):
                charts.append(result)
            else:
                errors.append({"index": index, "error": result})
        return {"success": bool(charts), "charts": charts, "errors": errors}
