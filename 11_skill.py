# Khái niệm: Skill nạp theo nhu cầu — prompt chỉ có tên + mô tả; nội dung đầy đủ được tool load_skill nạp khi cần.
# Layer: Context
# Khóa học: W1 L3, W4 L2  ·  OpsDesk: M06
from pathlib import Path

from langchain.agents import create_agent
from langchain_core.tools import tool

from common import llm

MAX_STEPS = 5
SKILLS_DIR = Path(__file__).parent / "skills"


def read_skill(path: Path) -> dict:
    # File skill = phần đầu (name, description) giữa hai dòng '---' + phần thân (quy trình chi tiết).
    _, header, body = path.read_text(encoding="utf-8").split("---", 2)
    meta = dict(line.split(": ", 1) for line in header.strip().splitlines())
    return {"name": meta["name"], "description": meta["description"], "body": body.strip()}


SKILLS = {s["name"]: s for s in map(read_skill, sorted(SKILLS_DIR.glob("*.md")))}

# System prompt chỉ chứa DANH MỤC (vài dòng), không chứa nội dung skill.
CATALOG = "\n".join(f"- {s['name']}: {s['description']}" for s in SKILLS.values())
SYSTEM_PROMPT = (
    "Bạn là trợ lý IT Helpdesk. Trả lời ngắn gọn.\n"
    "Khi câu hỏi khớp một skill dưới đây, gọi load_skill(name) để đọc quy trình rồi làm theo đúng quy trình đó.\n"
    f"Skill có sẵn:\n{CATALOG}"
)


@tool
def load_skill(name: str) -> dict:
    """Nạp nội dung đầy đủ của một skill theo tên trong danh mục."""
    if name not in SKILLS:  # chỉ nạp tên có trong danh mục, không đọc đường dẫn tùy ý
        return {"status": "not_found", "data": None, "safe_message": f"Không có skill '{name}'."}
    print(f"  [skill] nạp '{name}' ({len(SKILLS[name]['body'])} ký tự)")
    return {"status": "ok", "data": SKILLS[name]["body"]}


print(f"System prompt ({len(SYSTEM_PROMPT)} ký tự):\n{SYSTEM_PROMPT}")

agent = create_agent(model=llm(), tools=[load_skill], system_prompt=SYSTEM_PROMPT)


def run(question: str) -> None:
    print(f"\n>>> {question}")
    result = agent.invoke({"messages": [{"role": "user", "content": question}]}, {"recursion_limit": 2 * MAX_STEPS})
    for m in result["messages"]:
        if m.type == "ai" and m.tool_calls:
            for call in m.tool_calls:
                print(f"  model xin gọi {call['name']}({call['args']})")
        elif m.type == "ai":
            print(f"  trả lời: {m.text}")
    used = [m.usage_metadata["input_tokens"] for m in result["messages"] if m.type == "ai"]
    print(f"  [token] input_tokens mỗi lần gọi model: {used}")


for q in [
    "Tôi bị khóa tài khoản do nhập sai mật khẩu nhiều lần, giờ sao?",
    "Tuần sau có bạn mới vào team design, cần chuẩn bị laptop thế nào?",
    "Máy in tầng 3 có hỗ trợ in màu không?",
]:
    run(q)
