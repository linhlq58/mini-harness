# Khái niệm: Agent = vòng lặp "model đề xuất tool -> code chạy tool -> trả kết quả lại cho model".
# Layer: Orchestration
# Khóa học: W1 L3  ·  OpsDesk: M03
import json

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from common import TICKETS, llm

MAX_STEPS = 5  # giới hạn cứng: agent không được lặp mãi


def get_ticket(ticket_id: str) -> dict:
    t = TICKETS.get(ticket_id.upper())
    return t if t else {"error": f"không có ticket {ticket_id}"}


# Mô tả tool cho model đọc (JSON schema). Model chỉ thấy cái này, không thấy code Python.
TOOL_SPECS = [{
    "type": "function",
    "function": {
        "name": "get_ticket",
        "description": "Tra trạng thái một ticket hỗ trợ IT theo mã, ví dụ T-1.",
        "parameters": {
            "type": "object",
            "properties": {"ticket_id": {"type": "string", "description": "Mã ticket, ví dụ T-1"}},
            "required": ["ticket_id"],
        },
    },
}]
TOOLS = {"get_ticket": get_ticket}  # tên -> hàm thật, do code giữ

model = llm().bind_tools(TOOL_SPECS)  # gửi kèm danh sách tool trong mỗi request


def run(question: str) -> None:
    print(f"\n>>> {question}")
    messages = [
        SystemMessage("Bạn là trợ lý IT Helpdesk. Dùng tool khi cần, trả lời ngắn gọn."),
        HumanMessage(question),
    ]
    for step in range(1, MAX_STEPS + 1):
        reply = model.invoke(messages)
        messages.append(reply)  # nhớ lại model vừa đề xuất gì
        if not reply.tool_calls:  # model không xin tool nữa -> đây là câu trả lời cuối
            # Ghi chú phiên bản: langchain-core 1.8 — content có thể là list block; .text lấy phần chữ.
            print(f"  [bước {step}] model trả lời: {reply.text}")
            return
        for call in reply.tool_calls:  # model chỉ ĐỀ XUẤT; code mới là bên chạy
            print(f"  [bước {step}] model xin gọi {call['name']}({call['args']})")
            result = TOOLS[call["name"]](**call["args"])
            print(f"  [bước {step}] code chạy tool -> {result}")
            messages.append(ToolMessage(json.dumps(result, ensure_ascii=False), tool_call_id=call["id"]))
    print(f"  [dừng] hết {MAX_STEPS} bước mà chưa có câu trả lời cuối")


for q in [
    "Ticket T-1 của tôi sao rồi?",
    "So sánh trạng thái T-1 và T-2 giúp tôi.",
    "Chào bạn!",
]:
    run(q)
