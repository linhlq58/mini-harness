# Khái niệm: Least privilege — mỗi specialist chỉ có tool của mình; scope theo vai trò kiểm tra trước khi tool chạy.
# Layer: Tools · Verification
# Khóa học: W1 L2–L3  ·  OpsDesk: M03, M05
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool

from common import DOCS, EMPLOYEES, TICKETS, llm

MAX_STEPS = 5

# Vai trò -> những LOẠI thao tác được phép (thô). Ownership ở 06 là từng ĐỐI TƯỢNG (mịn).
ROLE_SCOPES = {
    "employee": {"ticket:read", "kb:read"},
    "it_staff": {"ticket:read", "ticket:close", "kb:read"},
    "it_manager": {"ticket:read", "ticket:close", "kb:read"},
}


@dataclass(frozen=True)
class RequestContext:
    user_id: str
    role: str


def envelope(status: str, data=None, safe_message: str = "") -> dict:
    return {"status": status, "data": data, "safe_message": safe_message}


def missing_scope(ctx: RequestContext, scope: str) -> dict | None:
    # Gọi ở dòng ĐẦU mỗi tool: thiếu scope thì dừng trước khi chạm dữ liệu.
    if scope in ROLE_SCOPES[ctx.role]:
        return None
    print(f"  [scope] CHẶN: {ctx.user_id} ({ctx.role}) thiếu '{scope}'")
    return envelope("denied", safe_message="Vai trò của bạn không được làm thao tác này.")


@tool
def get_ticket(ticket_id: str, runtime: ToolRuntime[RequestContext]) -> dict:
    """Tra trạng thái một ticket hỗ trợ IT theo mã, ví dụ T-1."""
    ctx = runtime.context
    if denied := missing_scope(ctx, "ticket:read"):
        return denied
    t = TICKETS.get(ticket_id.upper())
    if t is None:
        return envelope("not_found", safe_message=f"Không có ticket {ticket_id}.")
    if t["owner"] != ctx.user_id:
        return envelope("denied", safe_message="Bạn không có quyền xem ticket này.")
    return envelope("ok", data=t)


@tool
def close_ticket(ticket_id: str, runtime: ToolRuntime[RequestContext]) -> dict:
    """Đóng một ticket hỗ trợ IT theo mã, ví dụ T-1."""
    if denied := missing_scope(runtime.context, "ticket:close"):
        return denied
    t = TICKETS.get(ticket_id.upper())
    if t is None:
        return envelope("not_found", safe_message=f"Không có ticket {ticket_id}.")
    t["status"] = "closed"
    return envelope("ok", data=t)


@tool
def search_docs(query: str, runtime: ToolRuntime[RequestContext]) -> dict:
    """Tìm tài liệu chính sách/hướng dẫn IT theo từ khóa, ví dụ 'mật khẩu', 'VPN'."""
    if denied := missing_scope(runtime.context, "kb:read"):
        return denied
    hits = [d for d in DOCS if d["title"].lower().split()[-1] in query.lower()]
    return envelope("ok", data=hits) if hits else envelope("not_found", safe_message="Không thấy tài liệu.")


# Mỗi specialist chỉ được trao đúng bộ tool của mình.
AGENTS = {
    "ticket": create_agent(model=llm(), tools=[get_ticket, close_ticket], context_schema=RequestContext,
                           system_prompt="Bạn là specialist về ticket IT. Dùng tool khi cần, trả lời ngắn gọn."),
    "knowledge": create_agent(model=llm(), tools=[search_docs], context_schema=RequestContext,
                              system_prompt="Bạn là specialist về chính sách IT. Dùng tool khi cần, trả lời ngắn gọn."),
}


def server_handle(agent_name: str, session_user: str, question: str) -> None:
    ctx = RequestContext(user_id=session_user, role=EMPLOYEES[session_user]["role"])
    print(f"\n>>> [{session_user} -> agent {agent_name}] {question}")
    result = AGENTS[agent_name].invoke(
        {"messages": [{"role": "user", "content": question}]}, {"recursion_limit": 2 * MAX_STEPS}, context=ctx
    )
    for m in result["messages"]:
        if m.type == "ai" and m.tool_calls:
            for call in m.tool_calls:
                print(f"  model xin gọi {call['name']}({call['args']})")
        elif m.type == "tool":
            print(f"  framework chạy tool -> {m.content}")
        elif m.type == "ai":
            print(f"  model trả lời: {m.text}")


server_handle("ticket", "an", "Đóng ticket T-1 của tôi giúp nhé.")
server_handle("ticket", "binh", "Đóng ticket T-1 giúp tôi.")
server_handle("knowledge", "an", "Chính sách mật khẩu là gì?")
