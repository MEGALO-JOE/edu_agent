#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：json_utils.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""
import json
from typing import Any, Dict

def extract_json_object(text: str) -> Dict[str, Any]:
    """
    从模型输出中“尽最大努力”提取 JSON 对象。

    为什么需要它：
    - LLM 有时会输出 ```json ... ``` 包裹
    - 有时会在 JSON 前后加解释文字
    - 我们要尽量从中切出一个合法 JSON，再交给 json.loads
    """
    t = text.strip()

    # 1) 去掉常见的代码块围栏
    if t.startswith("```"):
        # 兼容 ```json 或 ```
        t = t.removeprefix("```json").removeprefix("```").strip()
    if t.endswith("```"):
        t = t.removesuffix("```").strip()

    # 2) 定位 JSON 对象的起止：从第一个 { 到最后一个 }
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object boundaries found in LLM output.")

    candidate = t[start : end + 1].strip()

    # 3) 解析 JSON
    return json.loads(candidate)

