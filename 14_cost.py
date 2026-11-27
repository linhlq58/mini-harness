# Khái niệm: Token -> tiền (VND); cùng một câu hỏi, chi phí khác nhau theo topology (agent đơn vs router).
# Layer: Operations
# Khóa học: W1 L5  ·  OpsDesk: M07, M21
from typing import Literal

from langchain.agents import create_agent
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from pydantic import BaseModel

from common import DOCS, TICKETS, llm

# Giá GIẢ ĐỊNH (USD / 1 triệu token) — thay bằng bảng giá thật của gateway. Token suy luận tính như output.
PRICE = {"input_per_1m": 1.25, "output_per_1m": 10.0, "usd_vnd": 26_000}
VOLUME = {"requests_per_day": 500, "workdays_per_month": 22, "retry_rate": 0.10}  # 10% lượt phải chạy lại
QUESTION = "Ticket T-1 sao rồi, và chính sách mật khẩu là gì?"


class CostMeter(BaseCallbackHandler):  # được gọi sau MỖI lần gọi model, ở mọi tầng
    def __init__(self):
        self.calls, self.input, self.output = 0, 0, 0

    def on_llm_end(self, response, **kwargs):
        usage = response.generations[0][0].message.usage_metadata
        self.calls += 1
        self.input += usage["input_tokens"]
        self.output += usage["output_tokens"]

    def vnd(self) -> float:
        usd = self.input / 1e6 * PRICE["input_per_1m"] + self.output / 1e6 * PRICE["output_per_1m"]
        return usd * PRICE["usd_vnd"]


@tool
def get_ticket(ticket_id: str) -> dict:
    """Tra trạng thái một ticket hỗ trợ IT theo mã, ví dụ T-1."""
    return TICKETS.get(ticket_id.upper(), {"error": "không có"})


@tool
def search_docs(query: str) -> list:
    """Tìm tài liệu chính sách/hướng dẫn IT theo từ khóa, ví dụ 'mật khẩu', 'VPN'."""
    return [d for d in DOCS if d["title"].lower().split()[-1] in query.lower()]


def single_agent(question: str, config: dict) -> str:  # topology 1: như file 04, một agent giữ mọi tool
    agent = create_agent(model=llm(), tools=[get_ticket, search_docs],
                         system_prompt="Bạn là trợ lý IT Helpdesk. Dùng tool khi cần, trả lời ngắn gọn.")
    return agent.invoke({"messages": [{"role": "user", "content": question}]}, config)["messages"][-1].text


class Intent(BaseModel):
    agent: Literal["ticket", "knowledge"]
    question: str


class Route(BaseModel):
    intents: list[Intent]


def router(question: str, config: dict) -> str:  # topology 2: như file 08 (chạy tuần tự cho gọn; chi phí như nhau)
    specialists = {
        "ticket": create_agent(model=llm(), tools=[get_ticket], system_prompt="Specialist ticket. Trả lời ngắn."),
        "knowledge": create_agent(model=llm(), tools=[search_docs], system_prompt="Specialist chính sách. Trả lời ngắn."),
    }
    route = llm().with_structured_output(Route).invoke(
        [SystemMessage("Tách câu hỏi thành các ý: ticket hoặc knowledge."), HumanMessage(question)], config)
    parts = [specialists[i.agent].invoke({"messages": [{"role": "user", "content": i.question}]}, config)
             ["messages"][-1].text for i in route.intents]
    return llm().invoke([SystemMessage("Gộp thành một câu trả lời ngắn."), HumanMessage("\n".join(parts))], config).text


per_month = VOLUME["requests_per_day"] * VOLUME["workdays_per_month"] * (1 + VOLUME["retry_rate"])
print(f">>> {QUESTION}\n")
print(f"{'topology':<14}{'lần gọi':>8}{'input':>8}{'output':>8}{'VND/lượt':>11}{'VND/tháng':>14}")
for name, fn in [("agent đơn", single_agent), ("router", router)]:
    meter = CostMeter()
    answer = fn(QUESTION, {"callbacks": [meter]})  # callback đi theo config xuống mọi lời gọi model bên trong
    print(f"{name:<14}{meter.calls:>8}{meter.input:>8}{meter.output:>8}{meter.vnd():>11.1f}{meter.vnd() * per_month:>14,.0f}")
    print(f"{'':<14}trả lời: {answer[:90]}")
print(f"\n(tháng = {VOLUME['requests_per_day']} lượt/ngày × {VOLUME['workdays_per_month']} ngày × {1 + VOLUME['retry_rate']:.2f} vì retry)")
