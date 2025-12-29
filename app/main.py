import json
import logging

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from app.agent.core import generate_plan, run_tools
from app.agent.intent import classify_intent
from app.agent.memory.db import init_db
from app.agent.rag.answer import ask_with_rag
from app.agent.rag.db import init_rag_tables
from app.agent.rag.schemas import KBAskRequest
from app.agent.reply_templates import render_plan_reply
from app.agent.schemas import ChatRequest, ChatResponse
from app.agent.speaking_flow import speaking_next
from app.agent.state_store import get_state
from app.agent.text_stream import stream_text
from app.infra.logging import setup_logging, new_trace_id

setup_logging()
log = logging.getLogger("api")

app = FastAPI(title="Edu Agent MVP")
init_db()
init_rag_tables()


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    trace_id = new_trace_id()
    plan = await generate_plan(req.user_id, req.message)
    tool_results = await run_tools(req.user_id, plan) if plan.tool_calls else None

    # 仍然保留非流式版本（方便调试 / 兼容）
    reply_lines = []
    if plan.intent in ("tutor", "practice", "plan") and plan.steps:
        reply_lines.append("我给你一个可执行的建议：")
        for idx, s in enumerate(plan.steps, 1):
            reply_lines.append(f"{idx}. {s}")
    else:
        reply_lines.append(plan.steps[0] if plan.steps else "你希望我怎么陪你练？（例如口语/面试/解题）")

    if tool_results:
        reply_lines.append("\n我已帮你记录/查询了一些事项。")

    return ChatResponse(
        trace_id=trace_id,
        reply="\n".join(reply_lines),
        plan=plan,
        tool_results=tool_results,
    )


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    SSE 流式输出接口（核心：先路由，再决定走哪条链路）
    """
    trace_id = new_trace_id()

    async def event_gen():
        # 1) 先发 meta，便于前端/日志关联
        yield f"event: meta\ndata: {json.dumps({'trace_id': trace_id}, ensure_ascii=False)}\n\n"

        # 0) 如果用户已经在 speaking 会话中：不做 intent，直接继续状态机
        #    （因为状态机里有很多逻辑，你不希望它被 interrupt）
        state = get_state(req.user_id)
        if state.domain == "speaking":
            if state.stage == 'ONBOARDING':
                text, _ = await speaking_next(req.user_id, req.message)
                async for chunk in stream_text(text):
                    yield f"{chunk}\n\n"
                yield "event: done\ndata: [DONE]\n\n"
                return
            elif state.stage == 'PRACTICE':
                text, _ = await speaking_next(req.user_id, req.message)
                async for chunk in stream_text(text):
                    yield f"{chunk}\n\n"
                if state.stage == 'FEEDBACK':
                    text, _ = await speaking_next(req.user_id, req.message)
                    async for chunk in stream_text(text):
                        yield f"{chunk}\n\n"
                yield "event: done\ndata: [DONE]\n\n"
                return
        else:
            # 2) ✅ 最重要：先做 intent 分类
            intent_res = await classify_intent(req.message)
            state.domain = intent_res.domain

            # 3) ✅ speaking（口语/自我介绍）优先走状态机，不走 generate_plan
            #    这样你就不会再看到 next_steps/todos/title 这些伪字段污染
            if intent_res.domain == "speaking":
                text, _ = await speaking_next(req.user_id, req.message)
                async for chunk in stream_text(text):
                    yield f"{chunk}\n\n"
                yield "event: done\ndata: [DONE]\n\n"
                return

        # 4) 其他 domain 才走原来的 plan + tool
        plan = await generate_plan(req.user_id, req.message)
        tool_results = await run_tools(req.user_id, plan) if plan.tool_calls else None

        # 4.1 plan 场景：服务端模板输出（可控）
        if plan.intent == "plan":
            final_text = render_plan_reply(plan, tool_results)
            async for chunk in stream_text(final_text):
                yield f"data: {chunk}\n\n"
            yield "event: done\ndata: [DONE]\n\n"
            return

        # 4.2 非 plan：你可以暂时也用模板兜底（建议），避免 LLM 流式污染
        #     Day5 我们会把 speaking 的 FEEDBACK 才引入 LLM judge（结构化）
        fallback = "我可以帮你做口语陪练。你想练：自我介绍 / 项目介绍 / 行为面试（STAR）？"
        async for chunk in stream_text(fallback):
            yield f"data: {chunk}\n\n"

        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# 直接问知识库
@app.post("/kb/ask")
async def kb_ask(req: KBAskRequest):
    text, chunks = await ask_with_rag(req.message, k=req.k)
    return {
        "answer": text,
        "citations": [
            {
                "cite_key": c.cite_key,
                "title": c.title,
                "chunk_index": c.chunk_index,
                "chunk_id": c.chunk_id,
            }
            for c in chunks
        ],
    }


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
