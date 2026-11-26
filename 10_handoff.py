# Khái niệm: Handoff — chuyển hẳn quyền hội thoại sang agent khác; checkpointer + thread_id giữ nó qua nhiều lượt.
# Layer: Orchestration · Context
# Khóa học: W1 L3  ·  OpsDesk: M06
from typing import NotRequired

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import wrap_model_call
from langchain.tools import ToolRuntime, tool
from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from common import DOCS, llm

MAX_STEPS = 5
INCIDENTS = []


class HandoffState(AgentState):  # state mặc định (messages) + một ô nhớ: ai đang giữ hội thoại
    active_agent: NotRequired[str]


@tool
def search_docs(query: str) -> dict:
    """Tìm tài liệu chính sách/hướng dẫn IT theo từ khóa, ví dụ 'mật khẩu', 'VPN'."""
    hits = [d for d in DOCS if d["title"].lower().split()[-1] in query.lower()]
    return {"status": "ok" if hits else "not_found", "data": hits}


@tool
def transfer_to_security(reason: str, runtime: ToolRuntime) -> Command:
    """Chuyển hội thoại sang đội Security khi có sự cố bảo mật: phishing, lộ mật khẩu, mã độc."""
    print(f"  [handoff] helpdesk -> security, lý do: {reason}")
    return Command(update={  # không trả dữ liệu, mà SỬA STATE của hội thoại
        "active_agent": "security",
        "messages": [ToolMessage("Đã chuyển sang đội Security.", tool_call_id=runtime.tool_call_id)],
    })


@tool
def open_incident(summary: str) -> dict:
    """Mở một sự cố bảo mật để đội Security xử lý. Gọi một lần cho mỗi sự cố."""
    INCIDENTS.append(summary)
    return {"status": "ok", "data": {"incident_id": f"SEC-{len(INCIDENTS)}"}}


PROFILES = {
    "helpdesk": (
        "Bạn là trợ lý IT Helpdesk. Sự cố bảo mật thì chuyển cho security. Trả lời ngắn gọn.",
        [search_docs, transfer_to_security]),
    "security": (
        "Bạn là đội Security. Hướng dẫn người dùng từng bước xử lý sự cố, mở incident khi cần. Trả lời ngắn gọn.",
        [open_incident]),
}


@wrap_model_call  # chạy TRƯỚC mỗi lần gọi model: chọn prompt + tool theo active_agent trong state
def route_by_state(request, handler):
    active = request.state.get("active_agent", "helpdesk")
    prompt, tools = PROFILES[active]
    print(f"  [model] đang là: {active}")
    return handler(request.override(system_message=SystemMessage(prompt), tools=tools))


agent = create_agent(
    model=llm(),
    tools=[search_docs, transfer_to_security, open_incident],  # framework cần biết mọi tool để chạy được
    state_schema=HandoffState,
    middleware=[route_by_state],
    checkpointer=InMemorySaver(),  # lưu state sau mỗi lượt, theo thread_id
)


def chat(thread_id: str, text: str) -> None:
    print(f"\n>>> [thread {thread_id}] {text}")
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 2 * MAX_STEPS}
    result = agent.invoke({"messages": [{"role": "user", "content": text}]}, config)
    msgs = result["messages"]
    start = max(i for i, m in enumerate(msgs) if m.type == "human")  # chỉ in phần của lượt này
    for m in msgs[start + 1:]:
        if m.type == "ai" and m.tool_calls:
            print(f"  model xin gọi {[(c['name'], c['args']) for c in m.tool_calls]}")
        elif m.type == "ai":
            print(f"  trả lời: {m.text}")
    print(f"  [state] active_agent={result.get('active_agent', 'helpdesk')}, tổng {len(msgs)} messages trong thread")


chat("an-1", "Mật khẩu phải dài tối thiểu bao nhiêu ký tự?")
chat("an-1", "Tôi vừa bấm vào link lạ trong email, nó đòi nhập mật khẩu công ty.")
chat("an-1", "Tôi lỡ nhập mật khẩu rồi. Giờ làm gì tiếp?")
