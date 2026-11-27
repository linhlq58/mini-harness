# Khái niệm: Tracing LangSmith — gắn metadata/tags, đọc lại trace để phân loại lỗi, biến lỗi thành regression case.
# Layer: Operations
# Khóa học: W1 L4  ·  OpsDesk: M07
import json
import time
import uuid
import warnings
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.tracers.langchain import wait_for_all_tracers
from langsmith import Client

from common import EMPLOYEES, TICKETS, llm

# Ghi chú phiên bản: langsmith 0.16 đánh dấu list_runs/read_run/get_run_url là deprecated (bỏ sau 31/01/2027);
# API mới client.runs.* trả AsyncPaginator chưa dùng ổn định, nên tạm giữ API cũ.
warnings.filterwarnings("ignore", message=".*deprecated.*")

MAX_STEPS = 5
REGRESSION_CASES = []  # mỗi lỗi thật -> một case để eval chạy lại mãi về sau (file 29)
client = Client()  # đọc LANGSMITH_* từ .env; tracing bật bằng LANGSMITH_TRACING=true, không cần sửa code agent


@dataclass(frozen=True)
class RequestContext:
    user_id: str
    role: str


def envelope(status: str, data=None, safe_message: str = "") -> dict:
    return {"status": status, "data": data, "safe_message": safe_message}


@tool
def get_ticket(ticket_id: str, runtime: ToolRuntime[RequestContext]) -> dict:
    """Tra trạng thái một ticket hỗ trợ IT theo mã, ví dụ T-1."""
    if ticket_id.upper() == "T-3":
        raise ConnectionError("DB ticket timeout")  # lỗi hạ tầng CỐ Ý để có cái mà tìm trong trace
    t = TICKETS.get(ticket_id.upper())
    if t is None:
        return envelope("not_found", safe_message=f"Không có ticket {ticket_id}.")
    if t["owner"] != runtime.context.user_id:
        return envelope("denied", safe_message="Bạn không có quyền xem ticket này.")
    return envelope("ok", data=t)


agent = create_agent(model=llm(), tools=[get_ticket], context_schema=RequestContext,
                     system_prompt="Bạn là trợ lý IT Helpdesk. Dùng tool khi cần, trả lời ngắn gọn.")


def server_handle(session_user: str, question: str) -> uuid.UUID:
    ctx = RequestContext(user_id=session_user, role=EMPLOYEES[session_user]["role"])
    run_id = uuid.uuid4()  # tự đặt id cho trace để tìm lại được
    config = {"run_id": run_id, "run_name": "helpdesk_chat", "recursion_limit": 2 * MAX_STEPS,
              "metadata": {"user": session_user, "workload": "chat"}, "tags": ["mini-harness", "13_tracing"]}
    print(f"\n>>> [{session_user}] {question}")
    try:
        result = agent.invoke({"messages": [{"role": "user", "content": question}]}, config, context=ctx)
        print(f"  trả lời: {result['messages'][-1].text}")
    except Exception as e:
        print(f"  LỖI {type(e).__name__}: {e}")
    return run_id


def classify(tool_run) -> str:
    # Đọc span tool trong trace: có exception -> lỗi hạ tầng; không thì đọc status của envelope.
    if tool_run.error:
        return "transient" if "ConnectionError" in tool_run.error or "Timeout" in tool_run.error else "unknown"
    status = json.loads(tool_run.outputs["output"]["content"])["status"]
    return {"ok": "ok", "not_found": "business", "denied": "policy"}.get(status, "unknown")


def inspect_trace(run_id: uuid.UUID, user: str, question: str) -> None:
    for _ in range(15):  # trace lên server có độ trễ vài giây
        tool_runs = list(client.list_runs(trace_id=run_id, run_type="tool"))
        if tool_runs:
            break
        time.sleep(1)
    for tr in tool_runs:
        category = classify(tr)
        print(f"  [trace {str(run_id)[:8]}] {tr.name}({tr.inputs.get('ticket_id')}) -> {category}")
        if category != "ok":
            REGRESSION_CASES.append({"user": user, "input": question, "category": category, "trace_id": str(run_id)})


cases = [("an", "Ticket T-1 sao rồi?"), ("an", "Ticket T-2 sao rồi?"), ("an", "Ticket T-9 sao rồi?"), ("an", "Ticket T-3 sao rồi?")]
run_ids = [server_handle(u, q) for u, q in cases]
wait_for_all_tracers()  # đẩy hết trace lên server trước khi đọc lại

print("\n=== Đọc lại trace từ LangSmith ===")
print("Mở trace lỗi trên web:", client.get_run_url(run=client.read_run(run_ids[-1])))
for (user, question), run_id in zip(cases, run_ids):
    inspect_trace(run_id, user, question)

print("\nREGRESSION_CASES =")
for c in REGRESSION_CASES:
    print(" ", c)
