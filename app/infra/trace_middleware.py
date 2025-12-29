#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：trace_middleware.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""
from starlette.middleware.base import BaseHTTPMiddleware
from app.infra.logging import trace_id_var, new_trace_id

class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 允许客户端自己传 trace_id（方便排障），否则自动生成
        tid = request.headers.get("X-Trace-Id") or new_trace_id()

        # ContextVar 绑定到本次请求上下文
        token = trace_id_var.set(tid)
        try:
            response = await call_next(request)
            # 把 trace_id 写回响应头：前端/测试工具能看到
            response.headers["X-Trace-Id"] = tid
            return response
        finally:
            # ✅ 一定要 reset，避免串请求
            trace_id_var.reset(token)
