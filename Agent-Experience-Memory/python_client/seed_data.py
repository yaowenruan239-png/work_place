from __future__ import annotations

from typing import Any

from python_client.db import fetch_all
from python_client.experience_store import add_experience

EXPERIENCES = [
    {
        "title": "生成图表前必须检查字段名",
        "task_type": "data_visualization",
        "problem_pattern": "Agent 在用户要求生成图表时，直接使用猜测的列名进行绘图，导致 KeyError 或空图。",
        "cause": "数据表字段名可能与用户描述不一致，尤其是中文字段、别名字段或经过清洗后的字段。",
        "solution": "绘图前先读取并确认 DataFrame 的 columns，必要时向用户说明可用字段，再选择正确字段生成图表。",
        "prompt_hint": "生成图表前必须先检查实际字段名，不要基于用户自然语言描述编造列名。",
        "importance": 5,
    },
    {
        "title": "日期列需要先解析",
        "task_type": "data_analysis",
        "problem_pattern": "Agent 对日期列进行排序、筛选、重采样或时间聚合时，把字符串日期当作 datetime 使用。",
        "cause": "CSV、Excel 或数据库读取后的日期字段常常是字符串类型，直接比较会产生错误顺序或类型异常。",
        "solution": "在执行时间相关分析前，使用日期解析函数转换列类型，并检查无法解析的异常值。",
        "prompt_hint": "涉及日期筛选、排序、分组或重采样时，先确认日期列已解析为 datetime 类型。",
        "importance": 5,
    },
    {
        "title": "类别过多时不要直接画柱状图",
        "task_type": "data_visualization",
        "problem_pattern": "Agent 对高基数类别字段直接绘制柱状图，导致图表拥挤、标签重叠、无法解读。",
        "cause": "类别数量过多时，完整展示所有类别会降低可读性，也可能掩盖主要分布。",
        "solution": "先统计类别数量，类别过多时只展示 Top N，并将其他类别合并为“其他”或改用更合适的可视化方式。",
        "prompt_hint": "绘制类别分布前先检查类别数量；类别过多时优先展示 Top N，不要直接画完整柱状图。",
        "importance": 4,
    },
    {
        "title": "缺失值会影响数值统计",
        "task_type": "data_analysis",
        "problem_pattern": "Agent 在计算均值、总和、比例或相关性时没有检查缺失值，导致统计结果偏差或样本量不一致。",
        "cause": "缺失值可能被自动跳过、转为 NaN 或影响分母，不同函数的默认行为并不相同。",
        "solution": "数值统计前检查缺失值数量和比例，明确采用删除、填充或单独标记策略，并在结果中说明处理方式。",
        "prompt_hint": "做数值统计前必须检查缺失值，并说明缺失值处理策略。",
        "importance": 5,
    },
    {
        "title": "LLM 输出 JSON 容易格式错误",
        "task_type": "tool_call",
        "problem_pattern": "Agent 要求 LLM 输出 JSON 后直接解析，但模型输出包含 Markdown、注释、尾逗号或非转义字符，导致解析失败。",
        "cause": "LLM 生成内容不保证严格符合 JSON 标准，尤其在复杂嵌套结构或中文文本中更容易出错。",
        "solution": "提示模型只输出严格 JSON，并在解析前做格式校验；解析失败时保留原始输出并给出修复或重试逻辑。",
        "prompt_hint": "需要 JSON 时明确要求严格 JSON；解析失败必须保留原始输出，不要假设 LLM 输出一定合法。",
        "importance": 5,
    },
    {
        "title": "中文 PDF 导出可能字体乱码",
        "task_type": "report_generation",
        "problem_pattern": "Agent 导出包含中文内容的 PDF 报告时，出现方块字、乱码或字体缺失。",
        "cause": "默认 PDF 字体通常不支持中文，绘图库或报表库需要显式配置中文字体。",
        "solution": "导出 PDF 前检查运行环境中的中文字体，显式设置字体文件或使用支持中文的字体配置。",
        "prompt_hint": "生成中文 PDF 前必须确认中文字体配置，避免默认字体导致乱码。",
        "importance": 4,
    },
    {
        "title": "不要在未确认列类型时做聚合",
        "task_type": "data_analysis",
        "problem_pattern": "Agent 在没有确认列类型的情况下对字段执行 sum、mean、count 或 groupby 聚合，产生类型错误或无意义结果。",
        "cause": "数值列可能被读取为字符串，类别列可能包含混合类型，聚合函数对不同类型的行为差异很大。",
        "solution": "聚合前检查 dtypes 和样例值，必要时进行类型转换、异常值处理和字段语义确认。",
        "prompt_hint": "执行聚合前先检查列类型和样例值，不要对未确认类型的列直接聚合。",
        "importance": 5,
    },
    {
        "title": "绘图前应处理极端值",
        "task_type": "data_visualization",
        "problem_pattern": "Agent 直接绘制数值分布或趋势图，极端值压缩正常样本区间，导致图表主体不可读。",
        "cause": "异常值或极端值会拉伸坐标轴范围，使大多数数据点集中在很小区域。",
        "solution": "绘图前检查分位数、最大最小值和异常点；必要时使用截尾、对数坐标、分面或单独标注极端值。",
        "prompt_hint": "绘制数值图表前检查极端值，避免异常点扭曲坐标轴和图表解读。",
        "importance": 4,
    },
    {
        "title": "用户问题模糊时不要过度猜测",
        "task_type": "agent_reasoning",
        "problem_pattern": "Agent 面对模糊用户请求时，自行假设指标口径、时间范围或输出格式，最终结果偏离用户真实意图。",
        "cause": "用户没有提供足够约束时，过多隐含假设会造成错误分析或错误工具调用。",
        "solution": "先识别缺失关键信息；如果假设会显著影响结果，应向用户澄清，或明确列出假设后再继续。",
        "prompt_hint": "用户问题模糊且关键口径缺失时，不要过度猜测；先澄清或显式声明假设。",
        "importance": 5,
    },
    {
        "title": "工具执行失败后必须保留错误上下文",
        "task_type": "tool_call",
        "problem_pattern": "Agent 调用工具失败后只记录一句失败信息，没有保留输入参数、错误消息和堆栈，导致后续无法复盘。",
        "cause": "缺少错误上下文会让经验总结和问题定位变得困难，也会导致重复尝试相同错误调用。",
        "solution": "工具失败时记录 run_id、tool_name、输入参数、错误消息、堆栈和相关上下文，再决定是否重试或总结经验。",
        "prompt_hint": "工具执行失败后必须保留完整错误上下文，不要只记录笼统失败描述。",
        "importance": 5,
    },
]


def find_existing_experience_id(item: dict[str, Any]) -> int | None:
    rows = fetch_all(
        """
        SELECT id
        FROM experience_memories
        WHERE title = %s
          AND task_type = %s
          AND prompt_hint = %s
        ORDER BY id ASC
        LIMIT 1
        """,
        (
            item["title"],
            item["task_type"],
            item["prompt_hint"],
        ),
    )
    if not rows:
        return None
    return int(rows[0]["id"])


def main() -> None:
    inserted_count = 0
    skipped_count = 0

    for item in EXPERIENCES:
        existing_id = find_existing_experience_id(item)
        if existing_id is not None:
            skipped_count += 1
            print(f"skipped existing memory_id={existing_id}: {item['title']}")
            continue

        memory_id = add_experience(**item)
        inserted_count += 1
        print(f"inserted memory_id={memory_id}: {item['title']}")

    print(f"seed complete: inserted={inserted_count}, skipped={skipped_count}")


if __name__ == "__main__":
    main()
