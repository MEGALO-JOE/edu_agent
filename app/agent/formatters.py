#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：formatters.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""
from typing import Any, Dict, Optional

def format_plan_steps(plan: Dict[str, Any]) -> str:
    """
    把 plan 里的 steps 转成纯文本清单，避免把 JSON/字段名暴露给模型。
    这样模型更不容易“学你输入的结构”然后输出 daily_tasks/todos 之类字段。
    """
    steps = plan.get("steps") or []
    if not steps:
        return "（无）"
    lines = []
    for i, s in enumerate(steps, 1):
        lines.append(f"{i}. {s}")
    return "\n".join(lines)

def format_tool_results(tool_results: Optional[Dict[str, Any]]) -> str:
    """
    把工具执行结果格式化成纯文本，避免把内部结构直接喂给模型。
    Day3 我们只处理你现在的两个工具：create_todo / list_todos。
    """
    if not tool_results:
        return "（无）"

    lines = []
    for k, v in tool_results.items():
        # k 类似 "0:create_todo"
        if "create_todo" in k:
            # create_todo 返回 {"ok": True, "count": N}
            if isinstance(v, dict) and v.get("ok"):
                lines.append(f"- 已创建/更新待办，当前待办数量：{v.get('count')}")
            else:
                lines.append(f"- 创建待办失败：{v}")
        elif "list_todos" in k:
            items = (v or {}).get("items", []) if isinstance(v, dict) else []
            if not items:
                lines.append("- 当前没有待办")
            else:
                lines.append("- 当前待办：")
                for it in items:
                    title = it.get("title", "")
                    lines.append(f"  - {title}")
        else:
            # 其他工具先兜底打印（但仍是纯文本）
            lines.append(f"- 工具 {k} 返回：{v}")

    return "\n".join(lines)
