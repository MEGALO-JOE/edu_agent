#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：speaking_judge.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""
import logging

from app.agent.core import call_llm
from app.agent.json_utils import extract_json_object
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.schemas import SpeakingFeedback

log = logging.getLogger("speaking_judge")

JUDGE_PROMPT = """你是英语口语面试陪练的评审官（严格、专业、但友善）。
请你根据【题目】与【用户回答】，只输出一个合法 JSON（不要 markdown，不要解释文字）。
字段必须包含：
- overall_score (0-10)
- fluency_score (0-10)
- grammar_score (0-10)
- vocabulary_score (0-10)
- structure_score (0-10)
- top_mistakes: 字符串数组，最多3条（具体指出哪里不自然/哪里错）
- improved_version: 英文改写版本（更自然、更像面试表达）
- chinese_coaching: 中文建议数组，最多5条（每条要可执行）
- next_question: 下一道题（同主题，难度略提升）

评分参考（rubric）：
- Fluency：是否连贯、少停顿、句子是否完整
- Grammar：时态/主谓一致/冠词/介词等错误
- Vocabulary：词汇是否准确、是否更地道
- Structure：结构是否清晰（开头-要点-例子-结尾），是否有结果/数据

注意：
- 不要编造用户没说过的经历/数据
- 如果用户回答太短，要指出“信息不足”，并告诉如何补充
"""

async def judge_speaking_answer(question: str, answer: str) -> SpeakingFeedback:
    """
    用 LLM 对用户回答做评测与纠错，输出结构化反馈。
    这里的关键是：LLM 只负责“评审”，不负责“流程控制”。
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"{JUDGE_PROMPT}\n\n题目：{question}\n\n用户回答：{answer}",
        },
    ]

    raw = await call_llm(messages)
    log.info(f"llm_raw(judge)={raw[:400]}")  # 只打前 400 字，避免日志太大

    obj = extract_json_object(raw)  # 复用 Day2 的鲁棒 JSON 提取
    return SpeakingFeedback.model_validate(obj)  # Pydantic 校验，保证字段齐全
