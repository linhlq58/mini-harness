# Khái niệm: Gọi model = gửi một danh sách messages (system/user/assistant), nhận lại một message.
# Layer: Context
# Khóa học: W1 L2  ·  OpsDesk: M03
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from common import llm

model = llm()

# Lượt 1: system đặt vai trò, user hỏi.
messages = [
    SystemMessage("Bạn là trợ lý IT Helpdesk. Trả lời ngắn gọn, tối đa 2 câu."),
    HumanMessage("Tên tôi là An. Laptop của tôi chạy rất chậm, tôi nên làm gì trước?"),
]
print("=== Lượt 1: gửi", len(messages), "messages ===")
for m in messages:
    print(f"  [{m.type}] {m.content}")

reply = model.invoke(messages)  # một lời gọi HTTP tới gateway
print("\n[ai]", reply.content)
print("usage:", reply.usage_metadata)  # số token vào/ra = thứ bạn trả tiền

# Lượt 2a: CÓ gửi lại lịch sử -> model "nhớ".
history = messages + [AIMessage(reply.content), HumanMessage("Tên tôi là gì?")]
print("\n=== Lượt 2a: gửi lại cả lịch sử (", len(history), "messages ) ===")
reply_a = model.invoke(history)
print("[ai]", reply_a.content)
print("usage:", reply_a.usage_metadata)

# Lượt 2b: KHÔNG gửi lịch sử -> model không biết gì về lượt trước.
alone = [messages[0], HumanMessage("Tên tôi là gì?")]
print("\n=== Lượt 2b: chỉ gửi câu hỏi mới (", len(alone), "messages ) ===")
reply_b = model.invoke(alone)
print("[ai]", reply_b.content)
print("usage:", reply_b.usage_metadata)
