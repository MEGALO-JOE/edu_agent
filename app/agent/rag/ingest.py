#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：ingest.py
@Author ：zqy
@Email : zqingy@work@163.com
@note: 文档切块 + 入库 + 建索引（ingest.py）
"""
import re
import time
from pathlib import Path
from typing import Iterable, List, Tuple

from app.agent.rag.db import get_conn, init_rag_tables

KB_DIR = Path("data/kb")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
BATCH_SIZE = 200  # 批量写入更大一些更快（可按需调）

CHUNK_MAX_CHARS = 700
CHUNK_OVERLAP = 80


def log(msg: str):
    """带时间戳的日志输出"""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def _normalize_text(s: str) -> str:
    # 把过多空行压缩一下，顺便去掉首尾空白
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _iter_chunks_from_text(text: str, max_chars: int = CHUNK_MAX_CHARS, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    纯文本切块（修复死循环版本）
    """
    if not text:
        return []
    if overlap >= max_chars:
        raise ValueError(f"overlap({overlap}) must be < max_chars({max_chars})")

    chunks: List[str] = []
    i = 0
    n = len(text)

    while i < n:
        end = min(i + max_chars, n)
        chunk = text[i:end].strip()
        if chunk:
            chunks.append(chunk)

        if end == n:  # ✅ 到末尾了必须退出，否则 i 可能卡住
            break

        next_i = end - overlap
        if next_i <= i:  # ✅ 双保险防止卡住
            break
        i = next_i

    return chunks


def _iter_chunks_streaming(path: Path, max_chars: int = CHUNK_MAX_CHARS, overlap: int = CHUNK_OVERLAP) -> Iterable[str]:
    """
    真正流式切块：边读文件边生成 chunk，不把全文一次性加载进内存。
    逻辑：维护一个缓冲区 buffer，够长就吐出 chunk，并保留 overlap 部分。
    """
    if overlap >= max_chars:
        raise ValueError(f"overlap({overlap}) must be < max_chars({max_chars})")

    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        log(f"⚠️ 跳过超大文件: {path} ({file_size / 1024 / 1024:.1f} MB)")
        return

    log(f"📄 开始读取文件: {path} ({file_size / 1024:.1f} KB)")

    buffer = ""
    produced = 0

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            buffer += line

            # 控制 buffer 的空行密度（可选，但能防止空行爆炸）
            if "\n\n\n" in buffer:
                buffer = re.sub(r"\n{3,}", "\n\n", buffer)

            while len(buffer) >= max_chars:
                chunk = buffer[:max_chars].strip()
                if chunk:
                    produced += 1
                    yield chunk

                # 保留 overlap 部分
                buffer = buffer[max_chars - overlap :]

    # 文件读完，处理最后剩余内容
    buffer = _normalize_text(buffer)
    if buffer:
        # 最后一段可能仍然很长，复用非流式切块（已修复死循环）
        tail_chunks = _iter_chunks_from_text(buffer, max_chars=max_chars, overlap=overlap)
        for c in tail_chunks:
            produced += 1
            yield c

    log(f"✅ 读取完成: {path} (生成 chunk 数: {produced})")


def reindex_kb() -> None:
    """把 data/kb 下所有 .md/.txt 重新入库并重建索引"""
    log("🚀 开始重建 KB 索引")

    init_rag_tables()
    conn = get_conn()
    cur = conn.cursor()

    try:
        # 1) 清空旧索引
        log("🗑️ 清空旧数据...")
        cur.execute("DELETE FROM kb_chunk_fts")
        cur.execute("DELETE FROM kb_chunk")
        cur.execute("DELETE FROM kb_doc")
        conn.commit()
        log("✅ 旧数据已清空")

        # 2) 遍历文件入库
        log("📂 开始遍历文件目录...")
        paths = sorted([p for p in KB_DIR.glob("**/*") if p.suffix.lower() in {".md", ".txt"}])
        log(f"📊 共找到 {len(paths)} 个文档")

        total_chunks = 0

        for idx, p in enumerate(paths, start=1):
            log(f"\n[{idx}/{len(paths)}] 处理文件: {p}")

            title = p.stem
            cur.execute("INSERT INTO kb_doc(path, title) VALUES (?, ?)", (p.as_posix(), title))
            doc_id = cur.lastrowid
            log(f"📝 插入 kb_doc: {title} (doc_id={doc_id})")

            # 批量缓存
            pending_chunk_rows: List[Tuple[int, int, str]] = []
            pending_fts_rows: List[Tuple[int, str]] = []

            chunk_index = 0

            for chunk_text in _iter_chunks_streaming(p):
                # 先插入 kb_chunk 以拿到 rowid(chunk_id)，fts 用 rowid 对齐
                cur.execute(
                    "INSERT INTO kb_chunk(doc_id, chunk_index, content) VALUES (?, ?, ?)",
                    (doc_id, chunk_index, chunk_text),
                )
                chunk_id = cur.lastrowid
                cur.execute(
                    "INSERT INTO kb_chunk_fts(rowid, content) VALUES (?, ?)",
                    (chunk_id, chunk_text),
                )

                chunk_index += 1
                total_chunks += 1

                if total_chunks % BATCH_SIZE == 0:
                    conn.commit()
                    log(f"💾 批量提交: 已处理 {total_chunks} 块")

            conn.commit()
            log(f"✅ 文档完成: {p} (chunks={chunk_index})")

        log(f"\n🎉 索引重建完成！共处理 {total_chunks} 块数据")

    except Exception as e:
        conn.rollback()
        log(f"❌ 索引重建失败，已回滚。错误: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    reindex_kb()
    print("KB reindexed ✅")
