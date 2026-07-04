from __future__ import annotations

import argparse
from pathlib import Path
from uuid import uuid4

from src.graph.builder import create_graph_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CSV-Insight-Agent from CLI")
    parser.add_argument("csv_path")
    parser.add_argument("query")
    parser.add_argument("--mode", choices=["quick_chart", "full_report", "planner_loop", "agent_loop"], default="quick_chart")
    args = parser.parse_args()
    state = {
        "run_id": uuid4().hex[:12],
        "mode": args.mode,
        "csv_path": args.csv_path,
        "csv_name": Path(args.csv_path).name,
        "user_query": args.query,
        "errors": [],
        "retry_count": 0,
        "status": "running",
    }
    print(create_graph_workflow().invoke(state))


if __name__ == "__main__":
    main()
