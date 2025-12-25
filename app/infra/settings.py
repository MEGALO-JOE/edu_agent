#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File ：settings.py
@Author ：zqy
@Email : zqingy@work@163.com 
@note: 
"""
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 先用 OpenAI 兼容接口举例；你也可以替换成任意兼容的网关/厂商
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"

    # agent 运行参数
    LLM_TIMEOUT_SEC: int = 30
    MAX_TOOL_STEPS: int = 4

settings = Settings()
