import json
import logging

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from app.agent.core import generate_plan, run_tools
from app.agent.intent import classify_intent
from app.agent.reply import stream_final_reply
from app.agent.reply_templates import render_plan_reply
from app.agent.schemas import ChatRequest, ChatResponse
from app.agent.speaking_flow import speaking_next
from app.agent.stream_utils import coalesce_chunks
from app.agent.text_stream import stream_text
from app.infra.logging import setup_logging, new_trace_id

setup_logging()
log = logging.getLogger("api")

app = FastAPI(title="Edu Agent MVP")


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
    SSE 流式输出接口：
    - 返回 text/event-stream
    - 客户端可以边接收边显示，体验更好
    """
    trace_id = new_trace_id()

    # 在生成 plan 之前先分类（更像真实架构：router 决策）
    intent_res = await classify_intent(req.message)

    async def event_gen():

        if intent_res.domain == "speaking":
            text, _ = speaking_next(req.user_id, req.message)
            async for chunk in stream_text(text):
                yield f"data: {chunk}\n\n"
        else:
            plan = await generate_plan(req.user_id, req.message)
            tool_results = await run_tools(req.user_id, plan) if plan.tool_calls else None

            # 先把 trace_id 发给前端（前端可用于关联日志/排障）
            yield f"event: meta\ndata: {json.dumps({'trace_id': trace_id}, ensure_ascii=False)}\n\n"

            # 再流式输出正文
            async for chunk in coalesce_chunks(stream_final_reply(req.message, plan.model_dump(), tool_results)):
                # SSE 协议格式：data: xxx\n\n
                yield f"data: {chunk}\n\n"

        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
