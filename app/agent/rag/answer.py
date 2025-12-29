#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：answer.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""
import logging
import re
from typing import Tuple, List

from app.agent.core import call_llm
from app.agent.rag.prompts import RAG_SYSTEM
from app.agent.rag.retriever import retrieve, RetrievedChunk

logger = logging.getLogger("rag")

_RAG_CACHE = {}  # key: (query, k) -> (text, chunks_meta)


def _extract_used_cite_keys(text: str) -> set[str]:
    # 从回答中提取所有引用的 cite_key，如 ["C1", "C2"]
    return set(re.findall(r"\[(C\d+)\]", text or ""))


def _has_valid_citations(text: str, chunks: List[RetrievedChunk]) -> bool:
    """
    检查回答中是否包含有效引用：
    - 至少引用一个 [C?]
    - 引用的编号必须存在于提供的 chunks
    """
    cite_keys = {c.cite_key for c in chunks}  # {"C1","C2"...}
    used = set(re.findall(r"\[(C\d+)\]", text or ""))
    if not used:
        return False
    return used.issubset(cite_keys)


def _build_context(chunks: List[RetrievedChunk]) -> str:
    """
    把检索到的 chunk 拼成带编号的上下文，供模型引用。
    """
    parts = []
    for c in chunks:
        parts.append(f"[{c.cite_key}] ({c.title}#{c.chunk_index})\n{c.content}\n")
    return "\n".join(parts)


async def ask_with_rag(query: str, k: int = 4) -> Tuple[str, List[RetrievedChunk]]:
    """
    返回：回答文本 + 引用 chunks（便于你在后处理里展示引用详情）
    """

    cache_key = (query, k)
    if cache_key in _RAG_CACHE:
        return _RAG_CACHE[cache_key]

    chunks = retrieve(query, k=k)

    logger.info(f"rag_retrieve query={query!r} got={len(chunks)}")
    if chunks:
        logger.info(f"rag_best_score={min(c.score for c in chunks)} titles={[c.title for c in chunks]}")

    # 经验阈值：bm25 越接近 0 越不相关；负数通常更相关 bm25越小越相关
    best_score = min([c.score for c in chunks]) if chunks else 0.0

    # 低相关/结果太少：拒答
    if (len(chunks) < 1) or (best_score > -0.05):
        return "资料不足：检索到的资料相关度不够，我不想胡编。请补充更具体的教材/题库/规则文档到 data/kb/。", []

    context = _build_context(chunks)

    user_prompt = f"""用户问题：
    {query}
    
    资料片段（请只基于这些资料回答）：
    {context}
    
    请输出：
    - 先给一个简短结论
    - 然后给 3-5 条可执行建议
    - 每条关键建议后面必须带引用，如 [C1]
    """

    messages = [
        {"role": "system", "content": RAG_SYSTEM},
        {"role": "user", "content": user_prompt},
    ]
    text = await call_llm(messages)
    # ✅ 引用校验：如果模型没按要求引用，就再严格重试一次
    if not _has_valid_citations(text, chunks):
        retry_prompt = user_prompt + "\n\n【注意】你刚才没有按要求引用。请重写，并确保每条关键建议后都带 [C1]/[C2] 引用，且不要引用不存在的编号。"
        messages = [
            {"role": "system", "content": RAG_SYSTEM},
            {"role": "user", "content": retry_prompt},
        ]
        text = await call_llm(messages)

    # 再不行就拒答（宁可不答，不胡答）
    if not _has_valid_citations(text, chunks):
        return "资料不足：我无法在保证引用合规的情况下回答。请补充更明确的资料或换一种问法。", chunks

    # 3) 过滤出实际被引用的 chunk
    used = _extract_used_cite_keys(text)
    if used:
        chunks = [c for c in chunks if c.cite_key in used]

    _RAG_CACHE[cache_key] = (text, chunks)
    return text, chunks
