# Khái niệm: Router — structured output chọn specialist -> chạy song song -> một bước tổng hợp; có fallback.
# Layer: Orchestration
# Khóa học: W1 L3  ·  OpsDesk: M05
import asyncio
import time
from dataclasses import dataclass
from typing import Literal

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from common import DOCS, EMPLOYEES, TICKETS, llm

MAX_STEPS = 5


@dataclass(frozen=True)
class RequestContext:
    user_id: str
    role: str


def envelope(status: str, data=None, safe_message: str = "") -> dict:
    return {"status": status, "data": data, "safe_message": safe_message}


@tool
def get_ticket(ticket_id: str, runtime: ToolRuntime[RequestContext]) -> dict:
    """Tra trạng thái một ticket hỗ trợ IT theo mã, ví dụ T-1."""
    t = TICKETS.get(ticket_id.upper())
    if t is None:
        return envelope("not_found", safe_message=f"Không có ticket {ticket_id}.")
    if t["owner"] != runtime.context.user_id:
        return envelope("denied", safe_message="Bạn không có quyền xem ticket này.")
    return envelope("ok", data=t)


@tool
def search_docs(query: str) -> dict:
    """Tìm tài liệu chính sách/hướng dẫn IT theo từ khóa, ví dụ 'mật khẩu', 'VPN'."""
    hits = [d for d in DOCS if d["title"].lower().split()[-1] in query.lower()]
    return envelope("ok", data=hits) if hits else envelope("not_found", safe_message="Không thấy tài liệu.")


AGENTS = {
    "ticket": create_agent(model=llm(), tools=[get_ticket], context_schema=RequestContext,
                           system_prompt="Bạn là specialist về ticket IT. Dùng tool khi cần, trả lời ngắn gọn."),
    "knowledge": create_agent(model=llm(), tools=[search_docs], context_schema=RequestContext,
                              system_prompt="Bạn là specialist về chính sách IT. Dùng tool khi cần, trả lời ngắn gọn."),
}


class Intent(BaseModel):  # hợp đồng dữ liệu: model BUỘC phải trả đúng hình dạng này
    agent: Literal["ticket", "knowledge"]
    question: str  # phần câu hỏi giao cho agent đó


class Route(BaseModel):
    intents: list[Intent]


ROUTER_PROMPT = ("Tách câu hỏi thành các ý, mỗi ý giao cho một agent: ticket (trạng thái ticket hỗ trợ) "
                 "hoặc knowledge (chính sách/hướng dẫn IT). Ngoài phạm vi IT thì trả intents rỗng.")
router = llm().with_structured_output(Route)  # trả về object Route, không phải chuỗi chữ


async def call_specialist(intent: Intent, ctx: RequestContext) -> str:
    t0 = time.perf_counter()
    result = await AGENTS[intent.agent].ainvoke(
        {"messages": [{"role": "user", "content": intent.question}]}, {"recursion_limit": 2 * MAX_STEPS}, context=ctx
    )
    answer = result["messages"][-1].text
    print(f"  [{intent.agent}] xong sau {time.perf_counter() - t0:.1f}s: {answer}")
    return f"[{intent.agent}] {answer}"


async def server_handle(session_user: str, question: str) -> None:
    ctx = RequestContext(user_id=session_user, role=EMPLOYEES[session_user]["role"])
    print(f"\n>>> [{session_user}] {question}")
    try:  # bước 1: route
        route = await router.ainvoke([SystemMessage(ROUTER_PROMPT), HumanMessage(question)])
    except Exception as e:
        print(f"  [router] LỖI {type(e).__name__} -> fallback")
        route = Route(intents=[])
    print(f"  [router] {[(i.agent, i.question) for i in route.intents]}")
    if not route.intents:  # fallback: không đoán bừa, trả lời an toàn
        print("  trả lời: Mình chỉ hỗ trợ ticket và chính sách IT. Bạn hỏi lại cụ thể hơn nhé.")
        return
    t0 = time.perf_counter()  # bước 2: các specialist chạy CÙNG LÚC
    parts = await asyncio.gather(*(call_specialist(i, ctx) for i in route.intents))
    print(f"  [song song] tổng {time.perf_counter() - t0:.1f}s")
    final = await llm().ainvoke([  # bước 3: gộp thành một câu trả lời
        SystemMessage("Gộp các câu trả lời của specialist thành một câu trả lời ngắn. Không thêm thông tin mới."),
        HumanMessage(f"Câu hỏi: {question}\n\n" + "\n".join(parts)),
    ])
    print(f"  trả lời: {final.text}")


async def main() -> None:
    for q in ["Ticket T-1 sao rồi, và chính sách mật khẩu là gì?", "Hướng dẫn VPN thế nào?", "Hôm nay ăn trưa gì ngon?"]:
        await server_handle("an", q)


asyncio.run(main())
