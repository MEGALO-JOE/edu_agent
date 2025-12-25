#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：reply.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note:
我们不对 “plan 生成”做流式（因为要 JSON 解析），而是：
先生成 plan
执行工具
再让模型根据 plan + tool_results 生成“最终回复”，这个最终回复用流式输出（体验更像真实产品）
"""
import logging
import httpx
from typing import AsyncGenerator, Dict, Any

from app.infra.settings import settings
from app.agent.prompts import SYSTEM_PROMPT
import json

log = logging.getLogger("reply")

def _looks_like_json_noise(s: str) -> bool:
    # 过滤明显的 JSON 外壳碎片，避免前端看到 { "response": 之类
    bad_tokens = ["{", "}", '"response"', '"', ":", "[", "]"]
    return s.strip() in bad_tokens


async def stream_final_reply(user_message: str, plan: Dict[str, Any], tool_results: Dict[str, Any] | None) -> AsyncGenerator[str, None]:
    """
    通过 OpenAI 兼容的 stream=true 来做流式输出（SSE）
    注意：不同厂商的流式字段可能不同，但大多数兼容 OpenAI 的都类似。
    """
    headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}

    prompt = (
        "请你直接对用户说话，输出【纯文本】最终回复。\n"
        "严禁输出 JSON、严禁输出花括号、严禁输出键名（如 response、plan 等）。\n"
        "如果你准备输出类似 { 或 \" 的字符，请立刻改写成自然语言。\n\n"
        f"用户输入：{user_message}\n"
        f"计划要点：{plan.get('steps')}\n"
        f"工具结果：{tool_results}\n"
    )

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT}, # 系统提示
            {"role": "user", "content": prompt}, # 用户输入
        ],
        "temperature": 0.3, # 控制输出的“随机”程度，0 到 1 之间
        "stream": True,  # 关键：开启流式
    }

    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SEC) as client:
        async with client.stream("POST", f"{settings.LLM_BASE_URL}/chat/completions", json=payload, headers=headers) as resp:
            resp.raise_for_status()

            # OpenAI 兼容流式：逐行读取 "data: {...}"
            async for line in resp.aiter_lines(): # 逐行读取
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line.removeprefix("data: ").strip()
                    if data == "[DONE]":
                        break

                    # 这里不做太复杂的容错，失败就跳过本行
                    try:
                        obj = json.loads(data) # 解析 JSON
                        delta = obj["choices"][0]["delta"].get("content")
                        if delta and not _looks_like_json_noise(delta):
                            yield delta
                    except Exception:
                        continue

