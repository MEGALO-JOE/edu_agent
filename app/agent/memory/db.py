#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：db.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""
import sqlite3
from pathlib import Path

# 数据库文件位置（也可以放到 settings 里做成可配置）
DB_PATH = Path("data/edu_agent.db")

def get_conn() -> sqlite3.Connection:
    """
    获取 SQLite 连接。
    - check_same_thread=False：允许在异步应用中跨线程使用（简化开发）
    - row_factory：让查询结果可以按 dict-like 方式取字段
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH.as_posix(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """
    初始化数据库表结构。
    这一步通常在服务启动时执行一次。
    """
    conn = get_conn()
    cur = conn.cursor()

    # 用户画像表：存 speaking 的长期信息（可逐步更新）
    cur.execute("""
    CREATE TABLE IF NOT EXISTS speaking_profile (
        user_id TEXT PRIMARY KEY,
        level TEXT,
        goal TEXT,
        daily_minutes INTEGER,
        preferred_style TEXT,       -- 例如: formal / casual
        updated_at INTEGER
    )
    """)

    # 练习记录表：每次题目 + 用户回答 + 评分 + 改写 + 下一题
    cur.execute("""
    CREATE TABLE IF NOT EXISTS speaking_attempt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        overall_score INTEGER,
        fluency_score INTEGER,
        grammar_score INTEGER,
        vocabulary_score INTEGER,
        structure_score INTEGER,
        top_mistakes TEXT,          -- 用 JSON 字符串存 list，简单易用
        improved_version TEXT,
        next_question TEXT,
        created_at INTEGER
    )
    """)

    conn.commit()
    conn.close()
