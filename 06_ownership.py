# Khái niệm: Tool tự kiểm tra ownership bằng code + trả về result envelope ok|not_found|denied.
# Layer: Verification
# Khóa học: W1 L2  ·  OpsDesk: M01–M03
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool

from common import EMPLOYEES, TICKETS, llm

MAX_STEPS = 5


@dataclass(frozen=True)  # frozen: tạo xong không ai sửa được
class RequestContext:
    user_id: str
    role: str


def envelope(status: str, data=None, safe_message: str = "") -> dict:
    # Hình dạng kết quả cố định cho MỌI tool: model và code đều đọc được trạng thái.
    return {"status": status, "data": data, "safe_message": safe_message}


@tool
def get_ticket(ticket_id: str, runtime: ToolRuntime[RequestContext]) -> dict:
    """Tra trạng thái một ticket hỗ trợ IT theo mã, ví dụ T-1."""
    ctx = runtime.context
    t = TICKETS.get(ticket_id.upper())
    if t is None:
        return envelope("not_found", safe_message=f"Không có ticket {ticket_id}.")
    if t["owner"] != ctx.user_id:  # kiểm tra ownership bằng CODE, trước khi lộ dữ liệu
        print(f"  [tool] CHẶN: {ctx.user_id} hỏi ticket của {t['owner']}")
        return envelope("denied", safe_message="Bạn không có quyền xem ticket này.")
    return envelope("ok", data=t)


@tool
def list_my_tickets(runtime: ToolRuntime[RequestContext]) -> list:
    """Liệt kê các ticket của chính người đang hỏi."""
    ctx = runtime.context  # đọc từ server, KHÔNG từ chat
    print(f"  [tool] thấy user_id={ctx.user_id}, role={ctx.role}")
    return [{"id": k, **v} for k, v in TICKETS.items() if v["owner"] == ctx.user_id]


agent = create_agent(
    model=llm(),
    tools=[get_ticket, list_my_tickets],
    system_prompt="Bạn là trợ lý IT Helpdesk. Dùng tool khi cần, trả lời ngắn gọn.",
    context_schema=RequestContext,  # khai báo kiểu context agent nhận
)


def server_handle(session_user: str, question: str) -> None:
    # "Server": danh tính lấy từ phiên đăng nhập (giả lập), vai trò tra từ dữ liệu nhân viên.
    ctx = RequestContext(user_id=session_user, role=EMPLOYEES[session_user]["role"])
    print(f"\n>>> [{session_user} đăng nhập] {question}")
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        {"recursion_limit": 2 * MAX_STEPS},
        context=ctx,  # đi đường riêng tới tool, không nằm trong messages
    )
    for m in result["messages"]:
        if m.type == "ai" and m.tool_calls:
            for call in m.tool_calls:
                print(f"  model xin gọi {call['name']}({call['args']})")
        elif m.type == "tool":
            print(f"  framework chạy tool -> {m.content}")
        elif m.type == "ai":
            print(f"  model trả lời: {m.text}")


server_handle("an", "Ticket T-1 của tôi sao rồi?")
server_handle("an", "Ticket T-2 sao rồi?")
server_handle("an", "Ticket T-9 sao rồi?")
