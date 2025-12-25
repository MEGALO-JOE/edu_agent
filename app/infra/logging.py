#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：logging.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""
import json
import logging
import sys
import uuid
from contextvars import ContextVar

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def new_trace_id() -> str:
    tid = uuid.uuid4().hex[:16]
    trace_id_var.set(tid)
    return tid


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
            "trace_id": trace_id_var.get(),
        }
        return json.dumps(payload, ensure_ascii=False)


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.handlers = [handler]
