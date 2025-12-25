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
    intent: Literal["tutor", "practice", "plan", "other"] = "other" # 计划意图
    """计划意图"""
    steps: List[str] = Field(default_factory=list) # 计划步骤
    tool_calls: List[ToolCall] = Field(default_factory=list) # 工具调用

class ChatResponse(BaseModel):
    """聊天响应"""
    trace_id: str = Field(description="跟踪ID")
    reply: str = Field(description="回复消息")
    plan: Optional[AgentPlan] = None # 计划
    tool_results: Optional[Dict[str, Any]] = None # 工具调用结果

class IntentResult(BaseModel):
    """意图识别结果"""
    intent: Literal["tutor", "practice", "plan", "other"]
    domain: Literal["speaking", "interview", "problem_solving", "unknown"] = "unknown"


class SpeakingProfile(BaseModel):
    """
    用户画像：陪练必须有“上下文”，否则就会瞎给建议
    """
    level: Optional[str] = None         # 例如 A2/B1/B2 或 “能日常交流/能面试”
    goal: Optional[str] = None          # 例如 “一周后面试自我介绍更流畅”
    daily_minutes: Optional[int] = None # 每天可投入分钟数

class SpeakingState(BaseModel):
    """
    状态机状态：服务端保存，不依赖模型记忆
    """
    stage: Literal["ONBOARDING", "PRACTICE", "FEEDBACK"] = "ONBOARDING"
    profile: SpeakingProfile = Field(default_factory=SpeakingProfile)
    last_question: Optional[str] = None