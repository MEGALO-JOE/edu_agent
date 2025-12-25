#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：text_stream.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""
import asyncio
from typing import AsyncGenerator

async def stream_text(text: str, chunk_size: int = 24, delay_ms: int = 15) -> AsyncGenerator[str, None]:
    """
    把一段完整文本，切成若干 chunk 逐步 yield，用于 SSE 流式输出。

    为什么要自己流式：
    - 计划类回复内容确定，不需要 LLM 来“编”
    - 自己流式可以保证：不出现 user_id/todos/title/JSON 等脏内容
    - 还能控制 chunk 大小和输出节奏，前端体验更自然
    """
    if not text:
        return

    # 按 chunk_size 切分
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]
        # 小延迟，模拟“打字机”效果（也能减少前端频繁刷新）
        await asyncio.sleep(delay_ms / 1000)
