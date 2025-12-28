#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：__init__.py.py
@Author ：zqy
@Email : zqingy@work@163.com
@note:
"""
"""



#  sqlite3 data/edu_agent.db ".tables"

## 查最近 5 条 attempt：
# -> sqlite3 data/edu_agent.db "select id,user_id,overall_score,fluency_score,grammar_score,vocabulary_score,structure_score,substr(question,1,30),substr(answer,1,30) from speaking_attempt order by id desc limit 5;"


sqlite3 data/edu_agent.db "select id, length(improved_version) as len_improved from speaking_attempt order by id desc limit 5;"


"""
