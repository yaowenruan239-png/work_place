from __future__ import annotations

from python_client.memory_client import ExperienceMemoryClient


QUERY = "用户让我画销售额随时间变化趋势图，但是我还不知道 CSV 里面有哪些字段。"


def main() -> None:
    client = ExperienceMemoryClient()
    memories = client.search(QUERY, top_k=3)
    prompt_context = client.build_prompt_context(memories)

    print("Search Results")
    for memory in memories:
        print(f"- memory_id={memory['id']} score={memory['score']:.4f} title={memory['title']}")
        print(f"  prompt_hint={memory['prompt_hint']}")

    print("\nPrompt Context")
    print(prompt_context)


if __name__ == "__main__":
    main()
