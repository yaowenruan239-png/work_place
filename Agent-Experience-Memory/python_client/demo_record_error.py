from __future__ import annotations

from python_client.error_collector import record_error


def main() -> None:
    try:
        raise ValueError("column sales_amount not found")
    except ValueError as exc:
        error_log_id = record_error(
            task_type="chart_generation",
            user_query="帮我画销售额趋势图",
            tool_name="plot_chart",
            error=exc,
            context={
                "columns": ["date", "amount", "region"],
                "dtypes": {
                    "date": "object",
                    "amount": "float64",
                    "region": "object",
                },
            },
        )
        print(f"inserted error_log_id={error_log_id}")


if __name__ == "__main__":
    main()
