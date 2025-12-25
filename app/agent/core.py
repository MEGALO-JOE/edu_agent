import logging
from typing import Any, Dict

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.agent.json_utils import extract_json_object
from app.agent.prompts import SYSTEM_PROMPT, PLAN_INSTRUCTION
from app.agent.schemas import AgentPlan
from app.agent.tools import TOOL_REGISTRY
from app.infra.settings import settings

log = logging.getLogger("agent")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=4))
async def call_llm(messages: list[dict]) -> str:
    """
    封装一次 LLM 调用，并带有指数退避重试。
    重试覆盖：网络抖动、5xx、短时限流等。
    :param messages: LLM 调用的消息列表
    :return: LLM 回复的文本
    """
    headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}
    payload = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "temperature": 0.2, # 控制输出的“随机”程度，0 到 1 之间
    }
    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SEC) as client:
        resp = await client.post(f"{settings.LLM_BASE_URL}/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

def _is_prompt_injection(text: str) -> bool:
    """
    Day2 先用关键字版的提示注入检测（入门）
    后续我们会升级到：分类器 + 规则 + 上下文隔离
    """
    bad = ["忽略之前", "system prompt", "输出系统提示", "developer message", "越狱", "jailbreak"]
    t = text.lower()
    return any(b.lower() in t for b in bad)

async def generate_plan(user_id: str, user_message: str) -> AgentPlan:
    """
    生成结构化 plan（Agent 的“控制塔”）

    核心工程点：
    - 任何时候都不要相信 LLM 输出一定是合法 JSON
    - 必须：解析失败 -> 让模型“修复输出” -> 再解析
    """
    if _is_prompt_injection(user_message):
        # 安全分支：直接拒绝，不进入工具调用
        return AgentPlan(
            intent="other",
            steps=["我无法遵循该请求。请告诉我你的学习目标或需要的陪练方式。"],
            tool_calls=[],
        )

    # 第一次请求：正常让模型输出 plan JSON
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"用户ID: {user_id}\n用户输入: {user_message}\n\n{PLAN_INSTRUCTION}"},
    ]

    raw = await call_llm(messages)
    log.info(f"llm_raw(plan)={raw[:500]}")

    # 解析 + 修复最多 2 次：总共最多 3 次尝试
    last_err = None
    for attempt in range(3):
        try:
            obj = extract_json_object(raw)  # 更鲁棒的提取
            return AgentPlan.model_validate(obj)  # Pydantic 校验结构
        except Exception as e:
            last_err = e
            # 让模型“修复输出”：
            # - 把错误原因告诉模型
            # - 明确要求：只输出 JSON，不要解释
            repair_msg = (
                "你刚才输出的内容无法被解析为合法 JSON。\n"
                f"错误信息：{repr(e)}\n\n"
                "请你只输出一个合法 JSON 对象（不要markdown，不要解释，不要额外文字），"
                "字段必须包含 intent/steps/tool_calls。"
            )
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": repair_msg})

            raw = await call_llm(messages)
            log.info(f"llm_raw(repair#{attempt+1})={raw[:500]}")

    # 三次都失败：给一个可控的降级 plan（不要让接口 500）
    log.error(f"generate_plan_failed err={repr(last_err)}")
    return AgentPlan(
        intent="other",
        steps=["我这次没能稳定生成计划。你能把需求再简短描述一次吗？比如：年级/科目/目标/每天时间。"],
        tool_calls=[],
    )

async def run_tools(user_id: str, plan: AgentPlan) -> Dict[str, Any]:
    """
    执行工具调用（对 LLM 的“可控执行层”）
    """
    results: Dict[str, Any] = {}
    for i, tc in enumerate(plan.tool_calls[: settings.MAX_TOOL_STEPS]):
        func = TOOL_REGISTRY.get(tc.name)
        if not func:
            results[f"{i}:{tc.name}"] = {"ok": False, "error": "tool_not_found"}
            continue

        # 安全：强制注入 user_id，防止模型传其他人的 user_id
        args = dict(tc.arguments or {})
        args["user_id"] = user_id

        try:
            results[f"{i}:{tc.name}"] = func(**args)
        except Exception as e:
            results[f"{i}:{tc.name}"] = {"ok": False, "error": str(e)}
    return results
