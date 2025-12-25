#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：state_store.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""
from typing import Dict
from app.agent.schemas import SpeakingState

# ✅ 开发阶段用内存 dict；线上会换 Redis/DB
SPEAKING_STORE: Dict[str, SpeakingState] = {}

def get_state(user_id: str) -> SpeakingState:
    """
    获取用户状态；没有就创建默认状态
    """
    if user_id not in SPEAKING_STORE:
        SPEAKING_STORE[user_id] = SpeakingState()
    return SPEAKING_STORE[user_id]

def save_state(user_id: str, state: SpeakingState) -> None:
    """
    保存用户状态
    """
    SPEAKING_STORE[user_id] = state
