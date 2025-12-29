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

DB_PATH = Path("data/edu_agent.db")

def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH.as_posix(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_rag_tables() -> None:
    """
    创建 RAG 用的表与 FTS5 索引。
    注意：SQLite 必须支持 FTS5（大多数 Python 自带 sqlite3 都支持）。
    """
    conn = get_conn()
    cur = conn.cursor()

    # 资料文档表
    cur.execute("""
    CREATE TABLE IF NOT EXISTS kb_doc (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      path TEXT UNIQUE NOT NULL,
      title TEXT NOT NULL
    )
    """)

    # 文档分块表：一份文档会被切成多个 chunk
    cur.execute("""
    CREATE TABLE IF NOT EXISTS kb_chunk (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      doc_id INTEGER NOT NULL,
      chunk_index INTEGER NOT NULL,
      content TEXT NOT NULL,
      FOREIGN KEY(doc_id) REFERENCES kb_doc(id)
    )
    """)

    # FTS5 索引：用于全文检索 kb_chunk.content
    # content_rowid='id'：让 FTS 表的 rowid 与 kb_chunk.id 对齐，方便 JOIN
    cur.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS kb_chunk_fts USING fts5(
      content,
      content_rowid='id'
    )
    """)

    conn.commit()
    conn.close()
