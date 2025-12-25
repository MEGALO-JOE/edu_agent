#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：stream_utils.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""
import time
from typing import AsyncGenerator

PUNCT = set("。！？!?；;\n")

async def coalesce_chunks(source: AsyncGenerator[str, None],
                          min_chars: int = 20,
                          max_wait_ms: int = 120) -> AsyncGenerator[str, None]:
    """
    把 LLM 的超碎 delta 聚合成更自然的 chunk 再输出给前端。

    为什么需要：
    - 有些模型/网关的 delta 会非常碎（甚至一个字）
    - 前端逐字刷屏体验差，也浪费 SSE 包数量
    """
    buf = []
    last_flush = time.time()

    async for piece in source:
        if not piece:
            continue

        buf.append(piece)

        now = time.time()
        joined = "".join(buf)

        # flush 条件 1：达到最小长度
        if len(joined) >= min_chars:
            yield joined
            buf.clear()
            last_flush = now
            continue

        # flush 条件 2：遇到标点/换行（优先保证语义完整）
        if any(ch in PUNCT for ch in piece):
            yield joined
            buf.clear()
            last_flush = now
            continue

        # flush 条件 3：等待时间过长（防止长时间无输出）
        if (now - last_flush) * 1000 >= max_wait_ms and joined:
            yield joined
            buf.clear()
            last_flush = now

    # 收尾：把剩余内容吐出去
    if buf:
        yield "".join(buf)
