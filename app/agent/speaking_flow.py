#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：speaking_flow.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note:  陪练逻辑（Day4 先做最小闭环）
"""
import re
from app.agent.schemas import SpeakingState
from app.agent.state_store import get_state, save_state

def _extract_minutes(text: str) -> int | None:
    """
    非严格解析：从用户输入里提取“每天多少分钟”
    例：'每天30分钟' -> 30
    """
    m = re.search(r"(\d{1,3})\s*分钟", text)
    if m:
        return int(m.group(1))
    return None

def speaking_next(user_id: str, user_message: str) -> tuple[str, SpeakingState]:
    """
    speaking 陪练状态机：
    输入：用户一句话
    输出：给用户的回复（纯文本） + 更新后的状态
    """
    state = get_state(user_id)

    # --------- ONBOARDING：收集画像 ----------
    if state.stage == "ONBOARDING":
        # 1) 尝试从本轮输入里补全画像（简单规则，后续可用 LLM 抽取）
        minutes = _extract_minutes(user_message)
        if minutes:
            state.profile.daily_minutes = minutes

        # 简单判断 level/goal（先用关键词，不够精也没关系）
        if any(k in user_message for k in ["A1", "A2", "B1", "B2", "C1", "C2"]):
            state.profile.level = user_message.strip()
        if any(k in user_message for k in ["面试", "自我介绍", "口语", "流利", "发音", "工作"]):
            state.profile.goal = user_message.strip()

        # 2) 如果画像还缺，就继续问（一次问一个，降低用户负担）
        if not state.profile.level:
            reply = "先快速了解你一下：你的英语口语水平大概是 A1-A2 / B1 / B2+，还是“能日常交流但不够流利”？"
            save_state(user_id, state)
            return reply, state

        if not state.profile.daily_minutes:
            reply = "你每天大概能投入多少分钟练口语？比如 15 / 30 / 45 分钟。"
            save_state(user_id, state)
            return reply, state

        if not state.profile.goal:
            reply = "你这一周最想提升的是：自我介绍、项目讲解、还是行为面试问题（STAR）？选一个就行。"
            save_state(user_id, state)
            return reply, state

        # 画像齐了，进入 PRACTICE
        state.stage = "PRACTICE"
        q = "我们开始模拟：请用英语做 30 秒自我介绍（包含：当前身份/擅长什么/最近一个项目亮点）。"
        state.last_question = q
        save_state(user_id, state)
        return q, state

    # --------- PRACTICE：等待用户回答 ----------
    if state.stage == "PRACTICE":
        # 用户这轮就是回答，我们下一轮给反馈
        state.stage = "FEEDBACK"
        save_state(user_id, state)
        reply = (
            "收到！我下一条会按三个维度给你反馈：\n"
            "1) 语法/用词\n"
            "2) 更地道的表达\n"
            "3) 结构与逻辑\n\n"
            "你也可以补充：你想偏“更正式面试风”还是“更自然口语风”？"
        )
        return reply, state

    # --------- FEEDBACK：给反馈 + 下一题 ----------
    if state.stage == "FEEDBACK":
        # Day4 先不调用 LLM 做精细纠错（明天 Day5 再接 LLM 评审器）
        reply = (
            "反馈（先给你一个通用模板，你照着替换内容就能更像面试表达）：\n"
            "- 开头：Hi, I’m ... I currently ...\n"
            "- 中段：I have experience in ... / I’m good at ...\n"
            "- 亮点：One project I’m proud of is ... (结果 + 数据)\n"
            "- 结尾：I’m excited about ... because ...\n\n"
            "下一题：请用英语回答：Tell me about a challenge you faced and how you solved it.（尽量按 STAR：Situation-Task-Action-Result）"
        )
        state.stage = "PRACTICE"
        state.last_question = "Tell me about a challenge you faced and how you solved it."
        save_state(user_id, state)
        return reply, state

    # 兜底
    save_state(user_id, state)
    return "我们继续口语陪练吧：你想练自我介绍还是行为问题？", state
