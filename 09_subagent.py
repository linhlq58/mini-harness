# Khái niệm: Subagent — agent chính gọi một agent con như gọi một tool; chỉ nhận lại kết quả cuối.
# Layer: Orchestration · Context
# Khóa học: W1 L3  ·  OpsDesk: M06
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool

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


# Agent con: giữ nguyên specialist knowledge của 07–08.
knowledge_agent = create_agent(model=llm(), tools=[search_docs],
                               system_prompt="Bạn là specialist về chính sách IT. Dùng tool khi cần, trả lời ngắn gọn.")


@tool
def ask_knowledge(question: str) -> str:
    """Hỏi chuyên gia chính sách IT (mật khẩu, VPN, laptop, phishing...). Truyền một câu hỏi đầy đủ."""
    print(f"  [subagent] nhận: {question}")
    result = knowledge_agent.invoke({"messages": [{"role": "user", "content": question}]},
                                    {"recursion_limit": 2 * MAX_STEPS})  # hội thoại RIÊNG, bắt đầu từ trống
    inner = result["messages"]
    print(f"  [subagent] nội bộ có {len(inner)} messages: {[m.type for m in inner]}")
    return inner[-1].text  # chỉ câu trả lời cuối đi ngược lên agent chính


# Agent chính: thấy ask_knowledge như một tool bình thường.
main_agent = create_agent(
    model=llm(),
    tools=[get_ticket, ask_knowledge],
    system_prompt="Bạn là trợ lý IT Helpdesk. Câu hỏi chính sách thì hỏi ask_knowledge. Trả lời ngắn gọn.",
    context_schema=RequestContext,
)


def server_handle(session_user: str, question: str) -> None:
    ctx = RequestContext(user_id=session_user, role=EMPLOYEES[session_user]["role"])
    print(f"\n>>> [{session_user}] {question}")
    result = main_agent.invoke(
        {"messages": [{"role": "user", "content": question}]}, {"recursion_limit": 2 * MAX_STEPS}, context=ctx
    )
    print(f"  [agent chính] có {len(result['messages'])} messages: {[m.type for m in result['messages']]}")
    for m in result["messages"]:
        if m.type == "ai" and m.tool_calls:
            for call in m.tool_calls:
                print(f"  agent chính xin gọi {call['name']}({call['args']})")
        elif m.type == "tool":
            print(f"  agent chính nhận -> {m.content}")
        elif m.type == "ai":
            print(f"  trả lời: {m.text}")


server_handle("an", "Ticket T-1 sao rồi, và mật khẩu phải dài bao nhiêu ký tự?")
