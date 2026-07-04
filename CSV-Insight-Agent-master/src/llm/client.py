from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from src.utils.json_utils import extract_json_object

load_dotenv()


@dataclass
class BackendConfig:
    name: str
    model: str
    api_key: str | None = None
    base_url: str | None = None


class LLMClient:
    def __init__(self, temperature: float = 0.1, max_retries: int = 2, backends: list[BackendConfig] | None = None):
        self.temperature = temperature
        self.max_retries = max_retries
        self.backends = self._detect_backends() if backends is None else backends
        self._active_backend = self.backends[0].name if self.backends else "rules"

    def available_backends(self) -> list[str]:
        return [backend.name for backend in self.backends]

    def active_backend(self) -> str:
        return self._active_backend

    def as_langchain_chat_model(self):
        if not self.backends:
            return None
        backend = self.backends[0]
        self._active_backend = backend.name
        if backend.name in {"deepseek", "openai"}:
            from langchain_openai import ChatOpenAI

            kwargs: dict[str, Any] = {
                "model": backend.model,
                "temperature": self.temperature,
                "api_key": backend.api_key,
            }
            if backend.base_url:
                kwargs["base_url"] = backend.base_url
            return ChatOpenAI(**kwargs)
        if backend.name == "ollama":
            from langchain_community.chat_models import ChatOllama

            return ChatOllama(model=backend.model, temperature=self.temperature)
        return None

    def chat(self, messages: list[dict[str, str]]) -> str:
        last_error: Exception | None = None
        for backend in self.backends:
            try:
                self._active_backend = backend.name
                return self._invoke_backend(backend, messages)
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"所有 LLM 后端调用失败: {last_error}")

    def chat_json(self, messages: list[dict[str, str]], schema: type[BaseModel] | None = None, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
        augmented = list(messages) + [{"role": "system", "content": "请只输出有效 JSON 对象，不要包含其他文字。"}]
        for attempt in range(self.max_retries):
            try:
                text = self.chat(augmented)
                data = extract_json_object(text)
                if schema:
                    return schema.model_validate(data).model_dump()
                return data
            except (ValueError, ValidationError, RuntimeError):
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    augmented.append({"role": "user", "content": "上次输出无法解析为合法 JSON。请重新输出。"})
        return fallback or {}

    def chat_json_with_trace(self, messages: list[dict[str, str]], schema: type[BaseModel] | None = None) -> dict[str, Any]:
        augmented = list(messages) + [{"role": "system", "content": "请只输出有效 JSON 对象，不要包含其他文字。"}]
        raw_text = ""
        data = None
        try:
            raw_text = self.chat(augmented)
        except RuntimeError as exc:
            return {"success": False, "phase": "llm_call", "error": str(exc), "raw_text": raw_text, "data": None}
        try:
            data = extract_json_object(raw_text)
        except ValueError as exc:
            return {"success": False, "phase": "llm_parse", "error": str(exc), "raw_text": raw_text, "data": None}
        if schema:
            try:
                validated = schema.model_validate(data).model_dump()
            except ValidationError as exc:
                return {"success": False, "phase": "validation", "error": str(exc), "raw_text": raw_text, "data": data}
            return {"success": True, "phase": "ok", "error": None, "raw_text": raw_text, "data": validated}
        return {"success": True, "phase": "ok", "error": None, "raw_text": raw_text, "data": data}

    def _detect_backends(self) -> list[BackendConfig]:
        backends: list[BackendConfig] = []
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        if deepseek_key:
            backends.append(
                BackendConfig(
                    "deepseek",
                    os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                    deepseek_key,
                    os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                )
            )
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            backends.append(BackendConfig("openai", os.getenv("OPENAI_MODEL", "gpt-4o-mini"), openai_key, None))
        if os.getenv("USE_OLLAMA", "false").lower() == "true":
            backends.append(BackendConfig("ollama", os.getenv("OLLAMA_MODEL", "llama3.1:8b")))
        return backends

    def _invoke_backend(self, backend: BackendConfig, messages: list[dict[str, str]]) -> str:
        langchain_messages = [(message["role"], message["content"]) for message in messages]
        if backend.name in {"deepseek", "openai"}:
            from langchain_openai import ChatOpenAI

            kwargs: dict[str, Any] = {
                "model": backend.model,
                "temperature": self.temperature,
                "api_key": backend.api_key,
            }
            if backend.base_url:
                kwargs["base_url"] = backend.base_url
            response = ChatOpenAI(**kwargs).invoke(langchain_messages)
            return str(response.content)
        if backend.name == "ollama":
            from langchain_community.chat_models import ChatOllama

            response = ChatOllama(model=backend.model, temperature=self.temperature).invoke(langchain_messages)
            return str(response.content)
        raise ValueError(f"Unknown backend: {backend.name}")
