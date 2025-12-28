#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：repo.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""
import json
import time
from typing import Optional, Dict, Any, List

from app.agent.memory.db import get_conn

def upsert_profile(user_id: str, level: Optional[str], goal: Optional[str],
                   daily_minutes: Optional[int], preferred_style: Optional[str] = None) -> None:
    """
    写入/更新用户画像（profile）。
    说明：
    - SQLite 不支持真正的 UPSERT 旧语法，我们用 INSERT ... ON CONFLICT 来做
    - updated_at 用 unix timestamp（秒）
    """
    conn = get_conn()
    cur = conn.cursor()
    now = int(time.time())

    cur.execute("""
    INSERT INTO speaking_profile (user_id, level, goal, daily_minutes, preferred_style, updated_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
      level = COALESCE(excluded.level, speaking_profile.level),
      goal = COALESCE(excluded.goal, speaking_profile.goal),
      daily_minutes = COALESCE(excluded.daily_minutes, speaking_profile.daily_minutes),
      preferred_style = COALESCE(excluded.preferred_style, speaking_profile.preferred_style),
      updated_at = excluded.updated_at
    """, (user_id, level, goal, daily_minutes, preferred_style, now))

    conn.commit()
    conn.close()

def get_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """
    读取用户画像。不存在返回 None。
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM speaking_profile WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def insert_attempt(user_id: str, question: str, answer: str, feedback: Dict[str, Any]) -> None:
    """
    写入一次练习记录（attempt）。
    feedback 是结构化结果（SpeakingFeedback.model_dump()）
    """
    conn = get_conn()
    cur = conn.cursor()
    now = int(time.time())

    cur.execute("""
    INSERT INTO speaking_attempt (
        user_id, question, answer,
        overall_score, fluency_score, grammar_score, vocabulary_score, structure_score,
        top_mistakes, improved_version, next_question, created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, question, answer,
        feedback.get("overall_score"),
        feedback.get("fluency_score"),
        feedback.get("grammar_score"),
        feedback.get("vocabulary_score"),
        feedback.get("structure_score"),
        json.dumps(feedback.get("top_mistakes", []), ensure_ascii=False),
        feedback.get("improved_version", ""),
        feedback.get("next_question", ""),
        now
    ))

    conn.commit()
    conn.close()

def get_recent_attempts(user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    获取最近 N 次练习记录。
    后续我们会用它做“个性化提示/出题”。
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    SELECT * FROM speaking_attempt
    WHERE user_id = ?
    ORDER BY id DESC
    LIMIT ?
    """, (user_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_avg_scores(user_id: str, last_n: int = 20) -> Dict[str, float]:
    """
    统计最近 N 次的平均分，用于判断薄弱项。
    SQL 聚合能让你展示“工程化能力”，面试很加分。
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    SELECT
      AVG(overall_score) AS overall,
      AVG(fluency_score) AS fluency,
      AVG(grammar_score) AS grammar,
      AVG(vocabulary_score) AS vocabulary,
      AVG(structure_score) AS structure
    FROM (
      SELECT * FROM speaking_attempt
      WHERE user_id = ?
      ORDER BY id DESC
      LIMIT ?
    )
    """, (user_id, last_n))
    row = cur.fetchone()
    conn.close()

    # SQLite AVG 可能返回 None（没有记录）
    def _v(x): return float(x) if x is not None else 0.0
    return {
        "overall": _v(row["overall"]),
        "fluency": _v(row["fluency"]),
        "grammar": _v(row["grammar"]),
        "vocabulary": _v(row["vocabulary"]),
        "structure": _v(row["structure"]),
    }
