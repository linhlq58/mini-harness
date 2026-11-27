# Khái niệm: Stream event của framework -> event riêng {seq, kind, payload} -> che PII -> có hạn giờ để hủy.
# Layer: Operations
# Khóa học: W1 L3, W2 L3  ·  OpsDesk: M02, M04
import asyncio
import re

from langchain.agents import create_agent
from langchain_core.tools import tool

from common import TICKETS, llm

MAX_STEPS = 5
DEADLINE_S = 30  # quá hạn thì hủy, không để người dùng chờ vô hạn


@tool
def get_ticket(ticket_id: str) -> dict:
    """Tra trạng thái một ticket hỗ trợ IT theo mã, ví dụ T-1."""
    t = TICKETS.get(ticket_id.upper())
    if t is None:
        return {"error": f"không có ticket {ticket_id}"}
    return t | {"contact": f"{t['owner']}@opsdesk.vn, 0912 345 678"}  # dữ liệu thật thường có PII


agent = create_agent(model=llm(), tools=[get_ticket],
                     system_prompt="Bạn là trợ lý IT Helpdesk. Dùng tool khi cần, trả lời ngắn gọn.")

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"(?:\+84|0)(?:[\s.]?\d){9}")
PII = re.compile(f"{EMAIL.pattern}|{PHONE.pattern}")
HOLD = 30  # giữ lại đuôi đủ dài: PII bị cắt giữa hai chunk vẫn bắt được


def redact(text: str) -> str:
    return PHONE.sub("[SĐT]", EMAIL.sub("[EMAIL]", text))


def split_safe(buf: str) -> tuple[str, str]:
    # Trả (phần đã an toàn để gửi, phần đuôi còn giữ lại chờ chunk sau).
    cut = max(0, len(buf) - HOLD)
    for m in PII.finditer(buf):
        if m.start() < cut < m.end():  # không cắt ngang một PII
            cut = m.end()
    return redact(buf[:cut]), buf[cut:]


def to_my_event(raw: dict) -> dict | None:
    # Chỉ giữ vài loại event mình cần; mọi thứ khác của framework bị bỏ.
    kind = raw["event"]
    if kind == "on_tool_start":
        return {"kind": "tool_start", "payload": {"tool": raw["name"], "args": raw["data"].get("input")}}
    if kind == "on_tool_end":
        return {"kind": "tool_end", "payload": {"tool": raw["name"], "result": redact(str(raw["data"]["output"].content))}}
    if kind == "on_chat_model_stream" and raw["data"]["chunk"].text:
        return {"kind": "token", "payload": raw["data"]["chunk"].text}  # chưa che: chờ gom đủ
    return None


async def stream(question: str):
    seq, buf = 0, ""
    try:
        async with asyncio.timeout(DEADLINE_S):  # hết giờ -> TimeoutError -> hủy luồng
            # Ghi chú phiên bản: langgraph 1.2 có thêm version="v3"; dùng "v2" như khóa học.
            async for raw in agent.astream_events(
                {"messages": [{"role": "user", "content": question}]}, {"recursion_limit": 2 * MAX_STEPS}, version="v2"
            ):
                event = to_my_event(raw)
                if event and event["kind"] == "token":
                    safe, buf = split_safe(buf + event["payload"])
                    event = {"kind": "token", "payload": safe} if safe else None
                if event:
                    seq += 1
                    yield {"seq": seq} | event
        if buf:  # xả nốt phần đuôi
            yield {"seq": seq + 1, "kind": "token", "payload": redact(buf)}
            seq += 1
        yield {"seq": seq + 1, "kind": "done", "payload": None}
    except TimeoutError:
        yield {"seq": seq + 1, "kind": "cancelled", "payload": f"quá {DEADLINE_S}s"}


async def main(question: str) -> None:
    print(f">>> {question}")
    async for e in stream(question):  # "UI" chỉ thấy event riêng, đã che PII
        if e["kind"] == "token":
            print(e["payload"], end="", flush=True)
        else:
            print(f"\n[{e['seq']:>3}] {e['kind']}: {e['payload']}")


asyncio.run(main("Ticket T-1 sao rồi? Cho tôi liên hệ của người tạo."))
