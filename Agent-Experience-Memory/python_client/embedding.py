from __future__ import annotations

from typing import Any

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_model: Any | None = None


def _get_model() -> Any:
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_text(text: str) -> list[float]:
    model = _get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return [float(value) for value in embedding.tolist()]


def build_memory_text(memory: dict[str, Any]) -> str:
    parts = [
        f"任务类型: {memory.get('task_type', '')}",
        f"问题模式: {memory.get('problem_pattern', '')}",
        f"原因: {memory.get('cause', '')}",
        f"解决方案: {memory.get('solution', '')}",
        f"提示词提醒: {memory.get('prompt_hint', '')}",
    ]
    return "\n".join(part for part in parts if part.strip())
