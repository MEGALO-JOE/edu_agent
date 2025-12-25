#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：tools.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""
from typing import Dict, Any
import time

# 真实项目这里会写数据库、任务队列、日程、检索等
FAKE_TODO_DB: Dict[str, list] = {}

def create_todo(user_id: str, title: str) -> Dict[str, Any]:
    time.sleep(0.05)  # 模拟IO
    FAKE_TODO_DB.setdefault(user_id, []).append({"title": title})
    return {"ok": True, "count": len(FAKE_TODO_DB[user_id])}

def list_todos(user_id: str) -> Dict[str, Any]:
    return {"ok": True, "items": FAKE_TODO_DB.get(user_id, [])}

TOOL_REGISTRY = {
    "create_todo": create_todo,
    "list_todos": list_todos,
}
