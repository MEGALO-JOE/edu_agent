#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：__init__.py.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""

"""
分块:
python -m app.agent.rag.ingest 

# 查询
sqlite3 data/edu_agent.db "select id, length(improved_version) as len_improved from speaking_attempt order by id desc limit 5;"

# 测试
 python -c "from app.agent.rag.retriever import retrieve; print(retrieve('STAR 方法怎么回答行为面试？请给我可执行建议', k=3))"
"""
