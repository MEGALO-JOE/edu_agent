#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：retriever.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""
import re
from dataclasses import dataclass
from typing import List

from app.agent.rag.db import get_conn


def _to_fts_query(user_query: str) -> str:
    """
    把用户自然语言 query 转为更稳定的 FTS5 查询字符串。

    为什么需要：
    - FTS MATCH 不是子串搜索，它吃的是“token查询语法”
    - 用户句子含标点、中文长句、空格等，会导致命中率不稳定甚至 0 命中

    策略：
    1) 先抽取英文/数字 token（最稳，例如 STAR / B1 / GPT）
    2) 再根据中文关键词做“同义扩展”（可控的规则，不依赖 LLM）
    3) 用 OR 连接，并用双引号包住 token，避免 FTS 语法歧义
    """
    q = (user_query or "").strip()
    if not q:
        return ""

    tokens: List[str] = []

    # 1) 抽取英文/数字 token（例如 STAR / B1 / SQL）
    tokens += re.findall(r"[A-Za-z0-9]+", q)

    # 2) 中文关键词 -> 扩展到知识库里更可能出现的词
    #    （这里是你教育产品的“可解释规则”，面试很加分）
    if "行为" in q or "STAR" in q.upper():
        tokens += ["STAR", "behavioral", "Situation", "Task", "Action", "Result"]

    if "自我介绍" in q:
        tokens += ["self", "introduction", "interview"]

    if "语法" in q or "B1" in q.upper():
        tokens += ["grammar", "B1", "articles", "tense"]

    # 去重（保持顺序）
    seen = set()
    uniq = []
    for t in tokens:
        tt = t.strip()
        if not tt:
            continue
        key = tt.lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(tt)

    # 3) 组装成 FTS 查询： "STAR" OR "behavioral" OR ...
    #    双引号可以避免 token 被当作语法操作符解析
    if uniq:
        return " OR ".join([f'"{t}"' for t in uniq])

    # 如果抽不到任何 token，就退回一个非常保守的查询（可能仍然命中率低）
    return f'"{q}"'


@dataclass
class RetrievedChunk:
    cite_key: str  # 例如 C1 / C2
    chunk_id: int
    title: str
    chunk_index: int
    content: str
    score: float  # SQLite bm25 分数（越小越相关，fts5 的 bm25 是“越小越好”）


def retrieve(query: str, k: int = 4) -> List[RetrievedChunk]:
    """
    使用 SQLite FTS5 检索最相关的 chunk。
    如果 query 太短或为空，直接返回空。
    """
    q = (query or "").strip()
    if len(q) < 2:
        return []

    fts_q = _to_fts_query(q)
    if not fts_q:
        return []

    conn = get_conn()
    cur = conn.cursor()

    # FTS5 的 MATCH 语法：直接用 query 做匹配
    # bm25(kb_chunk_fts) 可以得到相关度分数（越小越相关）
    cur.execute("""
                SELECT kb_chunk.id          AS chunk_id,
                       kb_doc.title         AS title,
                       kb_chunk.chunk_index AS chunk_index,
                       kb_chunk.content     AS content,
                       bm25(kb_chunk_fts)   AS score
                FROM kb_chunk_fts
                         JOIN kb_chunk ON kb_chunk.id = kb_chunk_fts.rowid
                         JOIN kb_doc ON kb_doc.id = kb_chunk.doc_id
                WHERE kb_chunk_fts MATCH ?
                ORDER BY score LIMIT ?
                """, (fts_q, k))

    rows = cur.fetchall()
    conn.close()

    # 2) 去重（相同 title + chunk_index 只保留一个）
    #    （因为 kb_chunk 里的 chunk_index 是按文档顺序严格递增的）
    seen = set()
    deduped_rows = []
    for r in rows:
        key = (str(r["title"]), int(r["chunk_index"]))
        if key in seen:
            continue
        seen.add(key)
        deduped_rows.append(r)

    rows = deduped_rows

    results: List[RetrievedChunk] = []
    for i, r in enumerate(rows, 1):
        results.append(
            RetrievedChunk(
                cite_key=f"C{i}",
                chunk_id=int(r["chunk_id"]),
                title=str(r["title"]),
                chunk_index=int(r["chunk_index"]),
                content=str(r["content"]),
                score=float(r["score"]),
            )
        )
    return results
