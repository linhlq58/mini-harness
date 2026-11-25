# Khái niệm: Cùng agent như 03 nhưng dùng create_agent — framework viết hộ vòng lặp; tool có type.
# Layer: Orchestration · Tools
# Khóa học: W1 L2–L3  ·  OpsDesk: M03
from langchain.agents import create_agent
from langchain_core.tools import tool

from common import TICKETS, llm

MAX_STEPS = 5  # vẫn cần giới hạn cứng; framework tính theo "bước của graph"


@tool
def get_ticket(ticket_id: str) -> dict:
    """Tra trạng thái một ticket hỗ trợ IT theo mã, ví dụ T-1."""
    t = TICKETS.get(ticket_id.upper())
    return t if t else {"error": f"không có ticket {ticket_id}"}


# @tool tự sinh JSON schema từ tên hàm + type hint + docstring (thay cho TOOL_SPECS viết tay ở 03).
print("Schema model sẽ thấy:", get_ticket.tool_call_schema.model_json_schema())

agent = create_agent(  # vòng lặp model -> tool -> model của 03 nằm gọn trong đây
    model=llm(),
    tools=[get_ticket],
    system_prompt="Bạn là trợ lý IT Helpdesk. Dùng tool khi cần, trả lời ngắn gọn.",
)


def run(question: str) -> None:
    print(f"\n>>> {question}")
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        {"recursion_limit": 2 * MAX_STEPS},  # mỗi vòng = 1 bước model + 1 bước tool
    )
    # Framework trả lại toàn bộ lịch sử; ta chỉ đọc lại để in ra, giống 03.
    for m in result["messages"]:
        if m.type == "ai" and m.tool_calls:
            for call in m.tool_calls:
                print(f"  model xin gọi {call['name']}({call['args']})")
        elif m.type == "tool":
            print(f"  framework chạy tool -> {m.content}")
        elif m.type == "ai":
            print(f"  model trả lời: {m.text}")


for q in [
    "Ticket T-1 của tôi sao rồi?",
    "So sánh trạng thái T-1 và T-2 giúp tôi.",
    "Chào bạn!",
]:
    run(q)
