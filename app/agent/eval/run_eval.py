#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：run_eval.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""
import json
import os
import sys
from statistics import mean


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, project_root)

from app.agent.memory.db import get_conn
from app.agent.speaking_judge import judge_speaking_answer

# CASES_PATH = Path("app/agent/eval/eval_cases.jsonl")

async def main():
    # cases = []
    # for line in CASES_PATH.read_text(encoding="utf-8").splitlines():
    #     if line.strip():
    #         cases.append(json.loads(line))
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
                select question, answer from speaking_attempt
                where user_id = ?
                order by id desc
                limit ?
                """, ("u5", 5))
    rows = cur.fetchall()
    conn.close()
    cases = [{"question": q, "answer": a} for q, a in rows]

    results = []
    for i, c in enumerate(cases, 1):
        fb = await judge_speaking_answer(c["question"], c["answer"])
        d = fb.model_dump()
        results.append(d)
        print(f"[{i}/{len(cases)}] overall={d['overall_score']} fluency={d['fluency_score']} grammar={d['grammar_score']}")

    # 简单统计
    summary = {
        "n": len(results),
        "overall_avg": mean([r["overall_score"] for r in results]),
        "fluency_avg": mean([r["fluency_score"] for r in results]),
        "grammar_avg": mean([r["grammar_score"] for r in results]),
        "vocabulary_avg": mean([r["vocabulary_score"] for r in results]),
        "structure_avg": mean([r["structure_score"] for r in results]),
    }
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
