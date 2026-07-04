from __future__ import annotations

from typing import Any, Callable

from src.utils.json_utils import extract_json_object

try:
    from langchain.agents import AgentExecutor, create_react_agent
except ImportError:  # LangChain 1.x removed the classic AgentExecutor API.
    AgentExecutor = None
    create_react_agent = None
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import BaseTool

from src.agent.langchain_tools import AgentRuntimeContext, build_langchain_tools
from src.agent.prompts import LANGCHAIN_REACT_SYSTEM_PROMPT
from src.experience_memory_adapter import get_experience_context
from src.agent.trace import steps_from_intermediate
from src.graph.nodes.planner_loop_node import build_default_registry
from src.llm.client import LLMClient
from src.skills.registry import SkillRegistry

ExecutorFactory = Callable[[list[BaseTool], PromptTemplate, BaseLanguageModel | None], Any]


class SimpleAgentAction:
    def __init__(self, tool: str, tool_input: dict[str, Any], log: str):
        self.tool = tool
        self.tool_input = tool_input
        self.log = log


class LangChainToolLoopExecutor:
    def __init__(self, tools: list[BaseTool], prompt: PromptTemplate, llm: BaseLanguageModel, max_iterations: int = 8):
        self.tools = {tool.name: tool for tool in tools}
        self.prompt = prompt
        self.llm = llm
        self.max_iterations = max_iterations

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        scratchpad = ""
        steps: list[tuple[SimpleAgentAction, Any]] = []
        for _ in range(self.max_iterations):
            rendered = self.prompt.format(
                input=payload.get("input", ""),
                tools=payload.get("tools", ""),
                tool_names=payload.get("tool_names", ""),
                agent_scratchpad=scratchpad,
            )
            response = self.llm.invoke(rendered)
            text = str(getattr(response, "content", response))
            if "Final Answer:" in text:
                return {"output": text.split("Final Answer:", 1)[1].strip(), "intermediate_steps": steps}
            try:
                action = extract_json_object(text)
            except ValueError:
                return {"output": text.strip(), "intermediate_steps": steps}
            tool_name = str(action.get("tool_name") or action.get("action") or "")
            tool_args = action.get("tool_args") or action.get("action_input") or {}
            thought = str(action.get("thought") or "")
            if tool_name in {"final_answer", "Final Answer"}:
                answer = tool_args.get("answer") if isinstance(tool_args, dict) else str(tool_args)
                return {"output": answer or thought, "intermediate_steps": steps}
            tool = self.tools.get(tool_name)
            if not tool:
                observation = {"success": False, "error": f"Unknown tool: {tool_name}"}
            else:
                observation = tool.invoke(tool_args if isinstance(tool_args, dict) else {"input": tool_args})
            steps.append((SimpleAgentAction(tool_name, tool_args if isinstance(tool_args, dict) else {"input": tool_args}, f"Thought: {thought}"), observation))
            scratchpad += f"Thought: {thought}\nAction: {tool_name}\nAction Input: {tool_args}\nObservation: {observation}\n"
        return {"output": "Agent Loop 达到最大步数，已返回当前中间结果。", "intermediate_steps": steps}


class LangChainCSVAgent:
    def __init__(
        self,
        registry: SkillRegistry | None = None,
        llm: BaseLanguageModel | None = None,
        executor_factory: ExecutorFactory | None = None,
        max_iterations: int = 8,
    ):
        self.registry = registry or build_default_registry()
        self.llm = llm
        self.executor_factory = executor_factory or self._default_executor_factory
        self.max_iterations = max_iterations

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        context = self.build_context(state)
        tools = build_langchain_tools(self.registry, context)
        prompt = self._build_prompt()
        executor = self.executor_factory(tools, prompt, self.llm or self._default_llm())
        response = executor.invoke(
            {
                "input": self._build_user_input(state, context),
                "tools": tools,
                "tool_names": ", ".join(tool.name for tool in tools),
                "agent_scratchpad": "",
            }
        )
        state.update(context.to_state_update())
        state["final_answer"] = str(response.get("output", ""))
        state["agent_steps"] = steps_from_intermediate(response.get("intermediate_steps", []))
        state["planner_steps"] = state["agent_steps"]
        state["status"] = "completed" if not context.errors else "fallback"
        return state

    @staticmethod
    def build_context(state: dict[str, Any]) -> AgentRuntimeContext:
        return AgentRuntimeContext(
            run_id=str(state.get("run_id", "")),
            csv_path=str(state.get("csv_path", "")),
            query=str(state.get("user_query", "")),
            profile=state.get("dataframe_profile", {}) or {},
            charts=state.get("generated_charts", []) or [],
            insights=state.get("analysis_insights", []) or [],
            markdown=state.get("report_markdown", "") or "",
            report_path=state.get("report_path", "") or "",
            pdf_path=state.get("pdf_path"),
            html_path=state.get("html_path"),
            errors=state.get("errors", []) or [],
        )

    def _default_executor_factory(self, tools: list[BaseTool], prompt: PromptTemplate, llm: BaseLanguageModel | None) -> Any:
        if llm is None:
            raise RuntimeError("LangChain Agent Loop 需要可用的 LangChain LLM。")
        if AgentExecutor is None or create_react_agent is None:
            return LangChainToolLoopExecutor(tools=tools, prompt=prompt, llm=llm, max_iterations=self.max_iterations)
        agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=False,
            return_intermediate_steps=True,
            handle_parsing_errors=True,
            max_iterations=self.max_iterations,
        )

    def _default_llm(self) -> BaseLanguageModel | None:
        return LLMClient().as_langchain_chat_model()

    def _build_prompt(self) -> PromptTemplate:
        template = LANGCHAIN_REACT_SYSTEM_PROMPT + """

可用工具：
{tools}

工具名称列表：{tool_names}

请严格使用以下格式：

Question: 用户问题
Thought: 你对下一步的思考
Action: 要调用的工具名，必须是 [{tool_names}] 之一
Action Input: 工具参数，必须是 JSON 对象
Observation: 工具返回结果
... 可以重复 Thought/Action/Action Input/Observation
Thought: 我已经完成任务
Final Answer: 最终中文回答，包含图表和报告路径

Question: {input}
{agent_scratchpad}"""
        return PromptTemplate.from_template(template)

    def _build_user_input(self, state: dict[str, Any], context: AgentRuntimeContext) -> str:
        experience_context = get_experience_context(
            user_query=context.query,
            task_type="csv_analysis",
        )
        memory_sections = [f"记忆上下文：{state.get('memory_context', '暂无历史记忆。')}"]
        if experience_context:
            memory_sections.append(f"经验记忆上下文：\n{experience_context}")
        memory_text = "\n\n".join(memory_sections)
        return (
            f"用户目标：{context.query}\n"
            f"CSV 路径：{context.csv_path}\n"
            f"运行 ID：{context.run_id}\n"
            f"{memory_text}\n"
            "请自动完成 CSV 数据画像、图表生成、洞察总结和报告导出。"
        )
