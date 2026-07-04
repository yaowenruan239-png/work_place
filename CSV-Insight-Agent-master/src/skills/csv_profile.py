from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from pandas.api.types import is_numeric_dtype

from src.skills.base import BaseSkill


class ProfileCSVSkill(BaseSkill):
    name = "profile_csv"
    description = "读取 CSV 并返回行列数、字段类型、缺失值、数值统计和样本数据。"
    args_schema = {"type": "object", "properties": {"csv_path": {"type": "string"}}, "required": ["csv_path"]}

    def run(self, **kwargs: Any) -> dict[str, Any]:
        csv_path = Path(kwargs["csv_path"])
        if not csv_path.exists():
            return {"success": False, "error": f"CSV 文件不存在: {csv_path}"}
        try:
            df = pd.read_csv(csv_path)
        except Exception as exc:
            return {"success": False, "error": f"CSV 读取失败: {exc}"}

        columns = list(df.columns)
        numeric_columns = [column for column in columns if is_numeric_dtype(df[column])]
        categorical_columns = [column for column in columns if column not in numeric_columns]
        return {
            "success": True,
            "file_name": csv_path.name,
            "rows": int(len(df)),
            "columns": int(len(columns)),
            "column_names": columns,
            "numeric_columns": numeric_columns,
            "categorical_columns": categorical_columns,
            "dtypes": {column: str(dtype) for column, dtype in df.dtypes.items()},
            "missing_values": {column: int(value) for column, value in df.isna().sum().items()},
            "numeric_summary": df[numeric_columns].describe().round(3).to_dict() if numeric_columns else {},
            "sample_rows": df.head(5).fillna("").to_dict(orient="records"),
        }
