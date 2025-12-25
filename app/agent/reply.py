import logging
import httpx
from typing import AsyncGenerator, Dict, Any, Optional

from app.infra.settings import settings
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.formatters import format_plan_steps, format_tool_results

log = logging.getLogger("reply")

def _looks_like_json_noise(s: str) -> bool:
    """
    过滤“明显是 JSON 结构碎片”的 token。
    你目前的输出里出现 daily_tasks": / todos": 这种，
    说明模型在输出字段名碎片，我们直接丢弃它们。

    注意：这是“输出侧兜底”，真正根治靠 prompt 不喂结构化 dict。
    """
    t = s.strip()

    # 一些非常短且明显的 JSON 符号
    if t in {"{", "}", "[", "]", ":", ",", '"', "```"}:
        return True

    # 含有 '":' 很像键值对结构，比如 daily_tasks":
    if '":' in t or t.endswith('":') or t.endswith('",'):
        return True

    # 像 key": 这种（字母下划线开头 + 引号冒号结尾），粗略判定为字段名碎片
    # 例如：daily_tasks":
    if t.replace("_", "").isalpha() and (t.endswith('":') or t.endswith('":') or t.endswith('": ')):
        return True

    return False

async def stream_final_reply(
    user_message: str,
    plan: Dict[str, Any],
    tool_results: Optional[Dict[str, Any]],
) -> AsyncGenerator[str, None]:
    """
    生成最终回复（流式）。
    核心原则：只让模型输出自然语言，不要让它“看见”你的内部 JSON 结构。
    """

    headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}

    # 关键：把 plan/tool_results 先格式化成“人类可读文本”，再喂给模型
    plan_text = format_plan_steps(plan)
    tool_text = format_tool_results(tool_results)

    prompt = (
        "你是教育陪练助手。请直接对用户输出【纯文本】回复。\n"
        "强约束（非常重要）：\n"
        "1) 只能输出自然语言文本，不允许输出 JSON/列表字典/字段名/代码块。\n"
        "2) 不要出现类似 daily_tasks、todos、plan、tool_results 等内部字段词。\n"
        "3) 给出清晰的下一步行动（可用项目符号），保持口语化。\n\n"
        f"用户输入：{user_message}\n\n"
        f"计划要点（仅供参考）：\n{plan_text}\n\n"
        f"已执行的动作结果（仅供参考）：\n{tool_text}\n"
    )

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SEC) as client:
        async with client.stream(
            "POST",
            f"{settings.LLM_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
        ) as resp:
            resp.raise_for_status()

            async for line in resp.aiter_lines():
                if not line:
                    continue
                if not line.startswith("data: "):
                    continue

                data = line.removeprefix("data: ").strip()
                if data == "[DONE]":
                    break

                try:
                    obj = __import__("json").loads(data)
                    delta = obj["choices"][0]["delta"].get("content")
                    if not delta:
                        continue

                    # 兜底过滤：丢弃 JSON/字段名碎片
                    if _looks_like_json_noise(delta):
                        continue

                    yield delta
                except Exception:
                    # 流式行解析失败，直接跳过即可（不要让接口崩）
                    continue
