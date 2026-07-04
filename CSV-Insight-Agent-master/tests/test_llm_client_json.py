from pydantic import BaseModel

from src.llm.client import LLMClient
from src.utils.json_utils import extract_json_object


def test_extract_plain_json():
    assert extract_json_object('{"mode": "quick_chart"}') == {"mode": "quick_chart"}


def test_extract_markdown_json_block():
    text = '```json\n{"mode": "full_report"}\n```'
    assert extract_json_object(text) == {"mode": "full_report"}


def test_extract_embedded_json_object():
    text = '前置说明 {"mode": "planner_loop", "reason": "需要自动规划"} 后置说明'
    assert extract_json_object(text) == {"mode": "planner_loop", "reason": "需要自动规划"}


def test_chat_json_returns_fallback_when_no_backends():
    client = LLMClient(backends=[], max_retries=1)
    result = client.chat_json([{"role": "user", "content": "hi"}], fallback={"ok": False})

    assert result == {"ok": False}


class RequiredName(BaseModel):
    name: str


class StaticLLMClient(LLMClient):
    def __init__(self, responses):
        super().__init__(backends=[])
        self.responses = list(responses)

    def chat(self, messages):
        if not self.responses:
            raise RuntimeError("no response")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_chat_json_with_trace_returns_parse_error():
    client = StaticLLMClient(["not json"])

    result = client.chat_json_with_trace([], schema=RequiredName)

    assert result["success"] is False
    assert result["phase"] == "llm_parse"
    assert "No JSON object found" in result["error"]
    assert result["raw_text"] == "not json"


def test_chat_json_with_trace_returns_validation_error():
    client = StaticLLMClient(['{"other":"value"}'])

    result = client.chat_json_with_trace([], schema=RequiredName)

    assert result["success"] is False
    assert result["phase"] == "validation"
    assert "name" in result["error"]
    assert result["data"] == {"other": "value"}
