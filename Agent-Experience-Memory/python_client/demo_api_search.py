from __future__ import annotations

import json
import os

import requests

API_URL = "http://127.0.0.1:8090/memory/search_context"

os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost")


def main() -> None:
    payload = {
        "query": "任务类型：csv_analysis\n用户问题：请分析每个月的销售金额趋势，并生成柱状图",
        "top_k": 3,
        "min_score": 0.25,
    }

    session = requests.Session()
    session.trust_env = False
    response = session.post(API_URL, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    print("Context")
    print(data.get("context", ""))
    print()
    print("Memories")
    print(json.dumps(data.get("memories", []), ensure_ascii=False, indent=2))

    warning = data.get("warning", "")
    if warning:
        print()
        print("Warning")
        print(warning)


if __name__ == "__main__":
    main()
