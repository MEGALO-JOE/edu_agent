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

## Day 5 - LLM Judge：把“口语陪练”做成可评审的闭环

### 当天目标
- 在口语陪练流程中引入 **LLM 评审器（Judge）**：对用户回答进行评分、纠错、改写，并给出下一题。
- 评审结果必须 **结构化输出（JSON）**，便于后续统计、回归评测、存档。

### 新增功能
- **SpeakingFeedback Schema（Pydantic）**
  - overall/fluency/grammar/vocabulary/structure 分项评分
  - top_mistakes（最多 3 条）
  - improved_version（更自然的英文版本）
  - chinese_coaching（中文可执行建议）
  - next_question（下一题）
- **speaking_judge.py**
  - 只允许 LLM 输出合法 JSON（禁止 markdown/解释文本）
  - 使用鲁棒 JSON 提取 + Pydantic 校验保证字段完整
- **speaking_render.py**
  - 将结构化反馈渲染为稳定的纯文本输出（避免 LLM 污染结构）

### 解决的问题
- 从“聊口语”升级为“可量化评审 + 可控纠错”
- 避免 LLM 直接生成最终回复导致的字段污染（如 todos/title 等）
- 为后续“记忆、评测、监控”建立标准数据结构


---

## Day 6 - Long-term Memory + Offline Eval：让产品可积累、可回归

### 当天目标
- 引入“长期记忆”：存用户画像与每次练习结果，形成可追踪的学习轨迹。
- 建立“离线评测”：用固定样例回归测试 judge 输出质量，形成工程闭环。

### 新增功能
- **SQLite 数据库（data/edu_agent.db）**
  - speaking_profile：用户画像（level/goal/daily_minutes 等）
  - speaking_attempt：每次练习记录（题目、回答、分项分数、错误点、改写、下一题）
- **memory/repo.py**
  - upsert_profile：更新用户画像
  - insert_attempt：写入练习记录
  - get_recent_attempts / get_avg_scores：读取近期记录、计算均分
- **离线评测框架**
  - eval_cases.jsonl：评测样例集
  - run_eval.py：批量调用 judge，输出 SUMMARY（平均分等）

### 解决的问题
- 让系统具备“持续学习轨迹”：用户越练越懂用户
- judge 输出可回归、可量化：可做版本对比、A/B、漂移监控
- 可在 README/面试中展示工程能力：数据、评测、可观测性闭环


---

## Day 7 - RAG + 引用规范 + 拒答策略：让回答有依据、可追溯

### 当天目标
- 给 Agent 增加“知识库检索能力（RAG）”，让建议来自资料而不是凭空生成。
- 强制引用来源（C1/C2...），资料不足时拒答，降低幻觉风险。

### 新增功能
- **知识库目录 data/kb/**
  - 支持 markdown/txt 资料（如自我介绍结构、STAR 方法、B1 语法等）
- **SQLite FTS5 全文检索**
  - kb_doc：文档元信息
  - kb_chunk：分块内容
  - kb_chunk_fts：FTS5 虚拟表（BM25 排序）
- **ingest/reindex**
  - 文档读取、清洗、切块（chunk+overlap）
  - 写入 kb_chunk 与 kb_chunk_fts
- **retrieve()**
  - Top-K chunk 检索并返回可引用编号（C1/C2…）
- **ask_with_rag()**
  - 组装上下文片段（含编号）
  - 强制模型按 [C1] 引用输出
  - 无检索结果或相关度不足 -> “资料不足”拒答
- **/kb/ask API**
  - 输入 message/k
  - 输出 answer + citations（cite_key/title/chunk_index/chunk_id）

### 解决的问题
- 建议可追溯：回答不再“看起来对但没依据”
- 降低幻觉：资料不足时不胡编
- 强可控：引用格式固定，便于后处理与审计


---

## Day 8 - RAG 工程加固：去重、引用过滤、体验优化

### 当天目标
- 让 RAG 输出更“干净可控”，避免重复引用、返回没用到的 citations。
- 优化 ACK 文案，避免误导用户“下一条才有反馈”。

### 新增功能 / 修复点
- **检索结果去重**
  - 同一 `(title, chunk_index)` 只保留一条，避免重复 chunk（如 star_method#0 出现两次）
- **只返回“实际被引用”的 citations**
  - 从 answer 中提取 `[C#]`，只保留对应 cite_key 的 chunks
  - citations 结构更严谨、更像产品
- **RAG 检索日志增强**
  - 打印 `rag_retrieve got=k`、`rag_best_score`、titles，便于诊断命中率与相关度
- **ACK 文案优化**
  - 将“我下一条会给你...”改为“收到✅我正在分析...”
  - 与同请求 SSE 输出完整反馈一致，不产生误导

### 解决的问题
- 引用更可信：返回的 citations 与文本一致
- 输出更精炼：避免重复来源/无关来源
- 产品体验更自然：同一次流式输出不再出现“下一条才反馈”的矛盾提示

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
