#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：intent.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""
import logging

from app.agent.core import call_llm
from app.agent.json_utils import extract_json_object
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.schemas import IntentResult

log = logging.getLogger("intent")

INTENT_PROMPT = """请对用户输入做意图分类，只输出合法 JSON：
字段：
- intent: tutor/practice/plan/other
- domain: speaking/interview/problem_solving/unknown

规则：
- 提到“口语/发音/对话/听说” => domain=speaking
- 提到“面试/自我介绍/行为问题/简历” => domain=interview
- 提到“解题/题目/步骤/推导/代码题” => domain=problem_solving
- 提到“计划/安排/日程/每日任务” => intent=plan
- 提到“陪练/练习/角色扮演/模拟” => intent=practice
- 提到“讲解/辅导/为什么/怎么理解” => intent=tutor
"""

async def classify_intent(user_message: str) -> IntentResult:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"用户输入：{user_message}\n\n{INTENT_PROMPT}"},
    ]
    raw = await call_llm(messages)
    log.info(f"llm_raw(intent)={raw[:200]}")
    obj = extract_json_object(raw)
    return IntentResult.model_validate(obj)

