import logging
from app.agent.core import call_llm
from app.agent.json_utils import extract_json_object
from app.agent.schemas import IntentResult
from app.agent.prompts import SYSTEM_PROMPT

log = logging.getLogger("intent")

INTENT_PROMPT = """请对用户输入做意图分类，只输出合法 JSON：
字段：
- intent: tutor/practice/plan/other
- domain: speaking/interview/problem_solving/unknown
"""

def classify_intent_rule_based(user_message: str) -> IntentResult:
    """
    规则分类器（优先使用）：
    好处：
    - 可控、稳定
    - 不花 LLM 成本
    - 面试时你能解释“为什么这么判”
    """

    msg = user_message.lower()

    # ---------- domain 规则：口语优先 ----------
    has_speaking = any(k in msg for k in ["口语", "发音", "对话", "听说", "spoken", "speaking"])
    has_interview = any(k in msg for k in ["面试", "自我介绍", "behavior", "interview", "简历"])
    has_problem = any(k in msg for k in ["解题", "题目", "推导", "证明", "算法题", "代码题", "leetcode"])

    # 优先级：speaking > problem_solving > interview
    if has_speaking:
        domain = "speaking"
    elif has_problem:
        domain = "problem_solving"
    elif has_interview:
        domain = "interview"
    else:
        domain = "unknown"

    # ---------- intent 规则 ----------
    has_plan = any(k in msg for k in ["计划", "安排", "日程", "每日任务", "一周", "规划"])
    has_practice = any(k in msg for k in ["陪练", "练习", "模拟", "角色扮演", "对练"])
    has_tutor = any(k in msg for k in ["讲解", "辅导", "为什么", "怎么理解", "帮我解释"])

    # intent 优先级：plan > practice > tutor > other
    if has_plan:
        intent = "plan"
    elif has_practice:
        intent = "practice"
    elif has_tutor:
        intent = "tutor"
    else:
        intent = "other"

    return IntentResult(intent=intent, domain=domain)

async def classify_intent(user_message: str) -> IntentResult:
    """
    最终对外的 intent 分类函数：
    1) 先规则分类
    2) 如果规则得出 unknown，再请求 LLM（兜底）
    """
    rule_result = classify_intent_rule_based(user_message)
    if rule_result.domain != "unknown":
        log.info(f"intent(rule)={rule_result.model_dump()}")
        return rule_result

    # 兜底：规则无法判断时才用 LLM
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"用户输入：{user_message}\n\n{INTENT_PROMPT}"},
    ]
    raw = await call_llm(messages)
    log.info(f"llm_raw(intent)={raw[:200]}")
    obj = extract_json_object(raw)
    llm_result = IntentResult.model_validate(obj)
    log.info(f"intent(llm)={llm_result.model_dump()}")
    return llm_result
