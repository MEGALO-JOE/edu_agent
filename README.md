# Edu Agent MVP（教育场景 Agent 应用基座）

一个面向教育场景的 **LLM Agent 工程化基座**：支持结构化计划（Plan）、工具调用（Tools）、SSE 流式输出（Streaming），并在第 4 天引入 **Intent 路由 + Speaking 陪练状态机**，将“聊天”升级为“可控的产品流程”。

---

## 目录
- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [4 天迭代总结](#4-天迭代总结)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [API 使用示例](#api-使用示例)
  - [/chat（非流式）](#chat非流式)
  - [/chat/stream（SSE 流式）](#chatstream-sse-流式)
- [测试](#测试)
- [设计要点](#设计要点)
- [Roadmap](#roadmap)

---

## 项目简介
本项目用于快速搭建教育场景的 Agent 应用能力，核心目标：
1. **可控执行**：LLM 输出必须结构化，工具调用必须白名单 + 参数校验
2. **工程可上线**：具备 API 封装、日志/trace、重试、流式体验、测试
3. **面向产品流程**：引入 intent 路由与状态机，减少模型跑偏、提升稳定性

---

## 功能特性
- ✅ FastAPI 服务化：`/chat`、`/chat/stream`
- ✅ LLM 调用封装：超时、重试（tenacity）
- ✅ 结构化输出：Pydantic schema 校验（Plan / Intent / State 等）
- ✅ 工具调用（Tools）：白名单、强制注入 `user_id` 防越权
- ✅ 安全防护（入门版）：提示注入关键字拦截
- ✅ SSE 流式输出：更好的用户体验
- ✅ 流式 chunk 聚合：减少逐字刷屏
- ✅ 单元测试：pytest 固化关键安全用例
- ✅ Intent 路由（规则优先）：稳定、省成本、可解释
- ✅ Speaking 陪练状态机 v1：ONBOARDING → PRACTICE → FEEDBACK（可控流程）

---

## 4 天迭代总结

### Day 1：跑通最小闭环 Agent（MVP）
**完成内容**
- 搭建 FastAPI 服务骨架，实现 `/chat`
- 实现最小 Agent：**生成计划（plan）→ 工具调用（tools）→ 回复（reply）**
- 引入 trace_id + JSON 日志

**新增能力**
- `AgentPlan` 结构化输出（Pydantic 校验）
- Fake Tools：
  - `create_todo(user_id, title)`
  - `list_todos(user_id)`
- 基础提示注入防护（关键字拦截）
- 工具调用安全：工具白名单 + 强制注入 `user_id`

**解决问题**
- 从“模型输出文本”升级为“可控执行的 Agent”
- 避免 LLM 乱传参导致越权风险

---

### Day 2：增强鲁棒性 + SSE 流式输出 + 单元测试
**完成内容**
- 新增 `/chat/stream`（SSE 流式输出）
- 增强结构化输出解析与重试
- 引入 pytest，固化关键安全用例

**新增能力**
- 鲁棒 JSON 提取/解析：兼容 ```json 包裹、前后夹杂文字等
- 解析失败修复重试：让模型重新输出合法 JSON（最多 3 次）
- SSE：先发送 `meta(trace_id)` 再输出正文
- pytest：注入请求必须被拒绝

**解决问题**
- LLM 输出不稳定导致的解析崩溃
- 提升对话体验（边生成边展示）
- 关键安全逻辑可回归

---

### Day 3：流式体验优化 + Intent 分类（为状态机路由打基础）
**完成内容**
- 优化 SSE 输出碎片化
- 引入 intent 分类（intent + domain），用于后续路由/状态机

**新增能力**
- chunk 聚合器：将超碎 delta 合并成更自然的 chunk
- intent 分类器（LLM 版）：
  - `intent: plan/practice/tutor/other`
  - `domain: speaking/interview/problem_solving/unknown`
- intent 日志输出（可观测）

**解决问题**
- 减少逐字刷屏，提升流式体验
- 从“模型自由发挥”走向“路由 + 固定流程”的工程路线

---

### Day 4：规则优先 Intent + Speaking 陪练状态机 v1（可控流程）
**完成内容**
- intent/domain 改为**规则优先**（不依赖 LLM，稳定且省成本）
- 正式引入 Speaking 状态机：ONBOARDING → PRACTICE → FEEDBACK
- 确定性场景优先服务端模板输出（减少字段污染风险）

**新增能力**
- 规则分类器：
  - speaking 优先级高于 interview（如“口语…面试”判 speaking）
  - plan/practice/tutor intent 规则判断
- Speaking 状态机 v1：
  - ONBOARDING：收集水平/目标/每天时间（一次问一个）
  - PRACTICE：出题（如 30 秒自我介绍）
  - FEEDBACK：先用模板给通用反馈并进入下一题（后续接 LLM 评审）
- 状态存储：内存 dict（后续可替换 Redis）
- 超低延迟返回（不经 LLM）

**解决问题**
- 彻底减少“对话跑偏”（比如练口语却输出学 Python 基础）
- 避免模型输出 `todos/title/user_id` 等伪结构字段污染

---

## 项目结构
（以当前实现为参考，可能随迭代略有调整）

```text
edu-agent/
  app/
    main.py
    agent/
      core.py              # LLM 调用 + plan 生成 + 工具执行
      prompts.py           # system/prompt 模板
      schemas.py           # Pydantic 数据结构（Plan/Intent/State）
      tools.py             # 工具注册表（Fake Tools）
      json_utils.py        # 鲁棒 JSON 提取
      stream_utils.py      # chunk 聚合器（减少逐字输出）
      intent.py            # intent/domain 分类（规则优先 + LLM 兜底）
      speaking_flow.py     # speaking 状态机
      state_store.py       # 状态存储（内存 dict）
      # reply.py            # （可选）非确定性场景的 LLM 流式回复
      # reply_templates.py  # （可选）确定性场景模板输出
      # text_stream.py      # （可选）服务端文本流式工具
    infra/
      logging.py           # JSON 日志 + trace_id
      settings.py          # 配置读取（.env）
  tests/
    test_agent.py          # 注入防护测试

```

## 快速开始
```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量（.env）
cp .env.example .env
# 编辑 .env，设置 LLM_API_KEY 等

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
