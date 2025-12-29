#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：speaking_flow.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note:  陪练逻辑（Day4 先做最小闭环）
"""
import logging
import re

from app.agent.rag.answer import ask_with_rag
from app.agent.schemas import SpeakingState
from app.agent.speaking_judge import judge_speaking_answer
from app.agent.speaking_render import render_feedback_text
from app.agent.state_store import get_state, save_state
from app.agent.memory.repo import upsert_profile, insert_attempt, get_avg_scores

logger = logging.getLogger(__name__)

def _extract_minutes(text: str) -> int | None:
    """
    非严格解析：从用户输入里提取“每天多少分钟”
    例：'每天30分钟' -> 30
    """
    m = re.search(r"(\d{1,3})\s*分钟", text)
    if m:
        return int(m.group(1))
    return None

def pick_rag_query(fb) -> str:
    """
    根据评分选择检索主题（非常像教育产品的个性化策略）。
    """
    # 先找最弱项
    scores = {
        "fluency": fb.fluency_score,
        "grammar": fb.grammar_score,
        "vocabulary": fb.vocabulary_score,
        "structure": fb.structure_score,
    }
    weakest = min(scores, key=scores.get)

    # 根据 weakest 决定查什么
    if weakest == "grammar":
        return "B1 grammar common issues tips"
    if weakest == "structure":
        return "STAR method behavioral questions structure"
    if weakest == "fluency":
        return "speaking fluency short complete sentences tips"
    # vocabulary
    return "self introduction interview structure 30-60 seconds"

async def speaking_next(user_id: str, user_message: str) -> tuple[str, SpeakingState]:
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
            state.profile.goal = ""
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

        upsert_profile(
            user_id=user_id,
            level=state.profile.level,
            goal=state.profile.goal,
            daily_minutes=state.profile.daily_minutes,
            preferred_style=None
        )

        return q, state

    # --------- PRACTICE：等待用户回答 ----------
    if state.stage == "PRACTICE":
        # 粗略估 token：英文 4 chars ~ 1 token，中文更复杂但先用字符数守门
        if len(user_message) > 1200:
            return "你的回答有点长（>1200字）。请缩短到 30-60 秒口语长度，我再给你更精准的纠错。", state

        # 用户这一轮是在回答题目，我们先把回答保存下来
        state.last_answer = user_message
        state.stage = "FEEDBACK"
        save_state(user_id, state)

        # 这里不调用 LLM（省钱），只是告诉用户“我将要反馈”
        reply = (
            "收到 ✅ 我正在分析你的回答（评分 + 纠错 + 改写 + 下一题）"
        )
        return reply, state

    # --------- FEEDBACK：给反馈 + 下一题 ----------
    elif state.stage == "FEEDBACK":
        # 取出上一题和用户回答，交给 LLM 做评审
        question = state.last_question or "Please do a 30-second self-introduction."
        answer = state.last_answer or ""

        # ✅ 这里才调用 LLM（成本集中在“反馈”而不是“闲聊”）
        try:
            fb = await judge_speaking_answer(question=question, answer=answer)
            logger.info(
                f"judge_scores={fb.overall_score}/{fb.fluency_score}/{fb.grammar_score}/{fb.vocabulary_score}/{fb.structure_score}")
        except Exception:
            # 降级：给通用反馈模板 + 下一题
            reply = "我这次没能稳定生成评分，但我给你一个通用改写模板...（略）下一题：..."
        else:

            insert_attempt(
                user_id=user_id,
                question=question,
                answer=answer,
                feedback=fb.model_dump()
            )

            # 渲染为纯文本（不让 LLM 直接输出最终回复，避免污染）
            reply = render_feedback_text(fb)

            avg = get_avg_scores(user_id, last_n=10)
            # 找到最低分项（简单 heuristic）
            weakest = min(
                [("fluency", avg["fluency"]), ("grammar", avg["grammar"]),
                 ("vocabulary", avg["vocabulary"]), ("structure", avg["structure"])],
                key=lambda x: x[1]
            )[0]
            logger.info(weakest)

            # 把 weakest 用在下一题提示或 coaching（最简单：在中文建议末尾追加一句）
            # 注意：这里不要改 fb 的结构字段（保持 judge 输出可控），你可以只在 render 阶段加一句
            #“你最近 10 次最弱项是：结构（5.5/10），下一轮我会重点要求你按 STAR 讲 Result。”
            reply += f"\n你最近 10 次最弱项是：{weakest.title()}（{avg[weakest]:.1f}/10），下一轮我会重点要求你按 {weakest.title()} 讲 Result。"

            rag_query = pick_rag_query(fb)
            rag_text, used_chunks = await ask_with_rag(rag_query, k=3)
            # 如果资料不足就不追加，避免污染输出
            if used_chunks:
                reply += "\n\n---\n基于资料的针对性建议（带引用）：\n"
                reply += rag_text

                # 可选：把引用来源列出来，用户看得更明白（非常加分）
                reply += "\n\n引用来源：\n"
                for c in used_chunks:
                    reply += f"- [{c.cite_key}] {c.title}#{c.chunk_index}\n"

            state.last_question = fb.next_question

        # 状态推进：下一轮继续 PRACTICE，题目更新为 next_question
        state.stage = "PRACTICE"
        state.last_answer = None
        save_state(user_id, state)

        return reply, state

    # 兜底
    save_state(user_id, state)
    return "我们继续口语陪练吧：你想练自我介绍还是行为问题？", state
