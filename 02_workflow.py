# Khái niệm: Workflow deterministic — code quyết định các bước, model chỉ làm một việc nhỏ (phân loại).
# Layer: Orchestration
# Khóa học: W1 L3  ·  OpsDesk: M05, M14a
import re

from langchain_core.messages import HumanMessage, SystemMessage

from common import DOCS, TICKETS, llm

model = llm()

LABELS = {"ticket", "policy", "other"}
CLASSIFY_PROMPT = (
    "Phân loại câu hỏi của nhân viên vào đúng MỘT nhãn: "
    "ticket (hỏi về ticket hỗ trợ của họ), policy (hỏi về quy định/hướng dẫn IT), other. "
    "Chỉ trả về đúng một từ: ticket, policy hoặc other."
)


def classify(question: str) -> str:
    # Việc DUY NHẤT của model trong file này.
    reply = model.invoke([SystemMessage(CLASSIFY_PROMPT), HumanMessage(question)])
    label = reply.content.strip().lower()
    print(f"  model trả về: {reply.content!r}")
    return label if label in LABELS else "other"  # code kiểm tra, không tin mù quáng


def handle_ticket(question: str) -> str:
    match = re.search(r"T-\d+", question.upper())
    if not match or match.group() not in TICKETS:
        return "Bạn cho mình mã ticket (ví dụ T-1) nhé."
    t = TICKETS[match.group()]
    return f"{match.group()} '{t['title']}' đang ở trạng thái: {t['status']}."


def handle_policy(question: str) -> str:
    for doc in DOCS:  # tìm thô: từ cuối của tiêu đề có trong câu hỏi không (RAG thật ở file 17)
        if doc["title"].lower().split()[-1] in question.lower():
            return f"[{doc['title']}] {doc['text']}"
    return "Mình chưa tìm thấy tài liệu phù hợp."


def handle_other(question: str) -> str:
    return "Mình chỉ hỗ trợ ticket và chính sách IT."


HANDLERS = {"ticket": handle_ticket, "policy": handle_policy, "other": handle_other}


def run(question: str) -> None:
    print(f"\n>>> {question}")
    label = classify(question)  # bước 1: model phân loại
    print(f"  nhãn dùng: {label}  ->  code gọi {HANDLERS[label].__name__}()")
    answer = HANDLERS[label](question)  # bước 2: code chọn nhánh, cố định
    print(f"  trả lời: {answer}")


for q in [
    "Ticket T-1 của tôi sao rồi?",
    "Chính sách mật khẩu là gì?",
    "Hôm nay ăn trưa gì ngon?",
]:
    run(q)
