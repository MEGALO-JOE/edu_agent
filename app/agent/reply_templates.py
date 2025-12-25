#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：reply_templates.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""
from typing import Any, Dict, Optional
from app.agent.schemas import AgentPlan

def render_plan_reply(plan: AgentPlan, tool_results: Optional[Dict[str, Any]]) -> str:
    """
    把 plan + tool_results 渲染成最终给用户看的文本（不经过 LLM）。

    设计原则：
    - 用户能看懂
    - 不暴露内部字段名
    - 输出可控稳定
    """
    lines = []
    lines.append("我给你一个可执行的一周口语提升安排（每天约45分钟）：")

    # plan.steps 是我们已经结构化好的建议
    if plan.steps:
        for idx, s in enumerate(plan.steps, 1):
            lines.append(f"{idx}. {s}")
    else:
        # 万一 plan 没 steps，也要给个兜底
        lines.append("1. 每天选一个主题练口语 20 分钟（先输出观点，再举例）。")
        lines.append("2. 每天复盘 10 分钟：把表达写下来，改成更自然的说法。")

    # 工具结果提示（如果你创建了待办）
    if tool_results:
        lines.append("")
        lines.append("我也帮你把关键任务记到待办里了。你想让我把每天的主题也细化出来吗？")

    return "\n".join(lines)
