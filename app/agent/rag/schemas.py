#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：schemas.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""
from pydantic import BaseModel, Field

class KBAskRequest(BaseModel):
    """
    单纯问知识库，不需要 user_id。
    """
    message: str = Field(..., description="用户问题/查询")
    k: int = Field(4, ge=1, le=10, description="检索 top-k")

