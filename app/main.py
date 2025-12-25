#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：main.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""
import logging
from fastapi import FastAPI
from app.infra.logging import setup_logging, new_trace_id
from app.agent.schemas import ChatRequest, ChatResponse
from app.agent.core import generate_plan, run_tools

setup_logging()
log = logging.getLogger("api")

app = FastAPI(title="Edu Agent MVP")

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    FastAPI 对话接口 /chat
    Agent 支持：意图识别 → 生成计划 → 工具调用 → 结构化输出
    有：日志、trace_id、错误重试、基本提示注入防护（入门版）
    :param req:
    :return:
    """
    # 生成计划
    trace_id = new_trace_id() # 生成trace_id
    plan = await generate_plan(req.user_id, req.message) # 生成计划
    tool_results = await run_tools(req.user_id, plan) if plan.tool_calls else None

    # 最简单的回复策略：把计划步骤整理成自然语言
    reply_lines = []
    if plan.intent in ("tutor", "practice", "plan") and plan.steps:
        reply_lines.append("我给你一个可执行的建议：")
        for idx, s in enumerate(plan.steps, 1):
            reply_lines.append(f"{idx}. {s}")
    else:
        reply_lines.append(plan.steps[0] if plan.steps else "你希望我怎么陪你练？（例如口语/面试/解题）")

    if tool_results:
        reply_lines.append("\n我已帮你记录/查询了一些事项。")

    return ChatResponse(
        trace_id=trace_id,
        reply="\n".join(reply_lines),
        plan=plan,
        tool_results=tool_results,
    )
