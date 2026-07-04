from src.skills.base import BaseSkill
from src.skills.registry import SkillRegistry


class EchoSkill(BaseSkill):
    name = "echo"
    description = "Echo input text"
    args_schema = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}

    def run(self, **kwargs):
        return {"success": True, "text": kwargs["text"]}


class BrokenSkill(BaseSkill):
    name = "broken"
    description = "Always fails"
    args_schema = {"type": "object", "properties": {}, "required": []}

    def run(self, **kwargs):
        raise RuntimeError("boom")


def test_register_and_call_skill():
    registry = SkillRegistry()
    registry.register(EchoSkill())

    result = registry.call("echo", text="hello")

    assert result == {"success": True, "text": "hello"}


def test_unknown_skill_returns_structured_error():
    registry = SkillRegistry()

    result = registry.call("missing")

    assert result["success"] is False
    assert "Unknown skill" in result["error"]
    assert "available_skills" in result


def test_skill_exception_uses_fallback():
    registry = SkillRegistry()
    registry.register(BrokenSkill())

    result = registry.call("broken")

    assert result["success"] is False
    assert "broken" in result["error"]


def test_list_skills_contains_schema():
    registry = SkillRegistry()
    registry.register(EchoSkill())

    skills = registry.list_skills()

    assert skills[0]["name"] == "echo"
    assert "args_schema" in skills[0]


def test_call_log_records_recent_calls():
    registry = SkillRegistry()
    registry.register(EchoSkill())

    registry.call("echo", text="hello")

    log = registry.get_call_log()
    assert log[-1]["skill"] == "echo"
    assert log[-1]["success"] is True
