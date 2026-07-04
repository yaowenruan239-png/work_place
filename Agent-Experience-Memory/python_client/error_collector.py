from __future__ import annotations

import json
import traceback
import uuid
from typing import Any

from python_client.db import execute


def record_error(
    task_type: str,
    user_query: str,
    tool_name: str,
    error: Exception | str,
    context: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> int:
    if run_id is None:
        run_id = str(uuid.uuid4())

    if isinstance(error, Exception):
        error_message = str(error)
        stack_trace = traceback.format_exc()
    else:
        error_message = error
        stack_trace = ""

    context_json = json.dumps(context or {}, ensure_ascii=False)

    return execute(
        """
        INSERT INTO agent_error_logs (
            run_id,
            task_type,
            user_query,
            tool_name,
            error_message,
            stack_trace,
            context_json
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            run_id,
            task_type,
            user_query,
            tool_name,
            error_message,
            stack_trace,
            context_json,
        ),
    )
