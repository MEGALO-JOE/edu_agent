#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：schemas.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any, List


class ChatRequest(BaseModel):
    """聊天请求"""
    user_id: str = Field(description="用户ID")
    message: str = Field(description="用户消息")


class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class AgentPlan(BaseModel):
    """计划"""
    intent: Literal["tutor", "practice", "plan", "other"] = "other"  # 计划意图
    """计划意图"""
    steps: List[str] = Field(default_factory=list)  # 计划步骤
    tool_calls: List[ToolCall] = Field(default_factory=list)  # 工具调用


class ChatResponse(BaseModel):
    """聊天响应"""
    trace_id: str = Field(description="跟踪ID")
    reply: str = Field(description="回复消息")
    plan: Optional[AgentPlan] = None  # 计划
    tool_results: Optional[Dict[str, Any]] = None  # 工具调用结果


class IntentResult(BaseModel):
    """意图识别结果"""
    intent: Literal["tutor", "practice", "plan", "other"]
    domain: Literal["speaking", "interview", "problem_solving", "unknown"] = "unknown"


class SpeakingProfile(BaseModel):
    """
    用户画像：陪练必须有“上下文”，否则就会瞎给建议
    """
    level: Optional[str] = None  # 例如 A2/B1/B2 或 “能日常交流/能面试”
    goal: Optional[str] = None  # 例如 “一周后面试自我介绍更流畅”
    daily_minutes: Optional[int] = None  # 每天可投入分钟数


class SpeakingState(BaseModel):
    """
    状态机状态：服务端保存，不依赖模型记忆
    """
    stage: Literal["ONBOARDING", "PRACTICE", "FEEDBACK"] = "ONBOARDING"  # 当前阶段[
    profile: SpeakingProfile = Field(default_factory=SpeakingProfile)
    last_question: Optional[str] = None
    last_answer: Optional[str] = None  # ✅ 新增：保存上一轮用户回答，供 FEEDBACK 评审
    domain: Literal["speaking", "interview", "problem_solving", "unknown"] = "unknown"



class SpeakingFeedback(BaseModel):
    """
    口语反馈结构（结构化的最大好处：可评测、可统计、可回归）
    """
    overall_score: int = Field(ge=0, le=10, description="总体评分 0-10")
    fluency_score: int = Field(ge=0, le=10, description="流利度 0-10")
    grammar_score: int = Field(ge=0, le=10, description="语法 0-10")
    vocabulary_score: int = Field(ge=0, le=10, description="词汇 0-10")
    structure_score: int = Field(ge=0, le=10, description="结构/逻辑 0-10")

    top_mistakes: List[str] = Field(default_factory=list, description="最重要的3个问题点")
    improved_version: str = Field(description="改写后的更自然版本（英文）")
    chinese_coaching: List[str] = Field(default_factory=list, description="中文建议（可执行）")
    next_question: str = Field(description="下一题（继续练）")
