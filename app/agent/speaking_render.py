#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：speaking_render.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note:
把结构化反馈渲染成“用户看得懂”的文本（纯文本、可控）
"""
from app.agent.schemas import SpeakingFeedback


def render_feedback_text(fb: SpeakingFeedback) -> str:
    """
    把结构化反馈转成纯文本输出。
    重要：这里不走 LLM，避免模型输出奇怪字段/结构。
    """
    lines = []
    lines.append("我给你做了口语反馈（10分制）：")
    lines.append(f"- 总分：{fb.overall_score}/10")
    lines.append(
        f"- 流利度：{fb.fluency_score}/10  语法：{fb.grammar_score}/10  "
        f"词汇：{fb.vocabulary_score}/10  结构：{fb.structure_score}/10"
    )
    lines.append("")

    if fb.top_mistakes:
        lines.append("你最需要优先改的 3 点：")
        for i, m in enumerate(fb.top_mistakes[:3], 1):
            lines.append(f"{i}. {m}")
        lines.append("")

    lines.append("更自然的表达（你可以直接照着说）：")
    lines.append(fb.improved_version.strip())
    lines.append("")

    if fb.chinese_coaching:
        lines.append("下一次你这样练会进步更快：")
        for i, tip in enumerate(fb.chinese_coaching[:5], 1):
            lines.append(f"{i}. {tip}")
        lines.append("")

    lines.append("下一题：")
    lines.append(fb.next_question.strip())

    return "\n".join(lines)
