# Khái niệm: Danh tính người dùng là RequestContext do server tạo, đi thẳng vào tool — không qua prompt.
# Layer: Context
# Khóa học: W1 L2  ·  OpsDesk: M02, M03
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool

from common import EMPLOYEES, TICKETS, llm

MAX_STEPS = 5


@dataclass(frozen=True)  # frozen: tạo xong không ai sửa được
class RequestContext:
    user_id: str
    role: str


@tool
def get_ticket(ticket_id: str) -> dict:
    """Tra trạng thái một ticket hỗ trợ IT theo mã, ví dụ T-1."""
    t = TICKETS.get(ticket_id.upper())
    return t if t else {"error": f"không có ticket {ticket_id}"}


@tool
def list_my_tickets(runtime: ToolRuntime[RequestContext]) -> list:
    """Liệt kê các ticket của chính người đang hỏi."""
    ctx = runtime.context  # đọc từ server, KHÔNG từ chat
    print(f"  [tool] thấy user_id={ctx.user_id}, role={ctx.role}")
    return [{"id": k, **v} for k, v in TICKETS.items() if v["owner"] == ctx.user_id]


# Tham số runtime bị ẩn: model không thấy, nên không thể điền giá trị giả vào.
print("Schema model thấy:", list_my_tickets.tool_call_schema.model_json_schema()["properties"])

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


server_handle("an", "Tôi có những ticket nào?")
server_handle("chi", "Tôi có những ticket nào?")
