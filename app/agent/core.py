import json
import logging
from typing import Any, Dict
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.infra.settings import settings
from app.agent.prompts import SYSTEM_PROMPT, PLAN_INSTRUCTION
from app.agent.schemas import AgentPlan, ToolCall
from app.agent.tools import TOOL_REGISTRY

log = logging.getLogger("agent")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=4))
async def call_llm(messages: list[dict]) -> str:
    headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}
    payload = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SEC) as client:
        resp = await client.post(f"{settings.LLM_BASE_URL}/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

def _is_prompt_injection(text: str) -> bool:
    bad = ["忽略之前", "system prompt", "输出系统提示", "developer message", "越狱", "jailbreak"]
    t = text.lower()
    return any(b.lower() in t for b in bad)

async def generate_plan(user_id: str, user_message: str) -> AgentPlan:
    if _is_prompt_injection(user_message):
        # 直接走安全分支：不给工具调用
        return AgentPlan(intent="other", steps=["我无法遵循该请求。请告诉我你的学习目标或需要的陪练方式。"], tool_calls=[])

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"用户ID: {user_id}\n用户输入: {user_message}\n\n{PLAN_INSTRUCTION}"},
    ]
    raw = await call_llm(messages)
    log.info(f"llm_raw={raw[:500]}")
    # 容错：有些模型会包 ```json
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    obj = json.loads(cleaned)
    return AgentPlan.model_validate(obj)

async def run_tools(user_id: str, plan: AgentPlan) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    for i, tc in enumerate(plan.tool_calls[: settings.MAX_TOOL_STEPS]):
        func = TOOL_REGISTRY.get(tc.name)
        if not func:
            results[f"{i}:{tc.name}"] = {"ok": False, "error": "tool_not_found"}
            continue
        # 强制注入 user_id（防止模型乱传别人的id）
        args = dict(tc.arguments or {})
        args["user_id"] = user_id
        try:
            results[f"{i}:{tc.name}"] = func(**args)
        except Exception as e:
            results[f"{i}:{tc.name}"] = {"ok": False, "error": str(e)}
    return results
