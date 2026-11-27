# Khái niệm: MCP client — nạp tool/resource từ server ngoài, gắn tiền tố tên, ép danh tính tin cậy, lỗi hạ tầng -> unavailable.
# Layer: Tools
# Khóa học: W2 L1  ·  OpsDesk: M08
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from mcp.types import CallToolResult, TextContent

from common import EMPLOYEES, llm

MAX_STEPS = 5
# Client tự khởi động server như một tiến trình con (stdio). Server thật thường chạy riêng qua HTTP.
CONNECTIONS = {"asset": {"transport": "stdio", "command": sys.executable,
                         "args": [str(Path(__file__).parent / "15_mcp_server.py")]}}


@dataclass(frozen=True)
class RequestContext:
    user_id: str
    role: str


def unavailable(reason: str) -> CallToolResult:
    body = {"status": "unavailable", "data": None, "safe_message": "Hệ thống tài sản tạm thời gián đoạn."}
    print(f"  [mcp] LỖI HẠ TẦNG: {reason} -> trả unavailable")
    return CallToolResult(content=[TextContent(type="text", text=json.dumps(body, ensure_ascii=False))])


async def trusted_call(request, handler):
    # Chạy ở CLIENT trước mọi lời gọi tool MCP: ghi đè danh tính, bắt lỗi hạ tầng.
    ctx = request.runtime.context
    args = request.args | {"user_id": ctx.user_id}  # model điền gì cũng bị thay bằng user thật
    print(f"  [mcp] {request.server_name}/{request.name}: model gửi {request.args} -> client gửi {args}")
    try:
        return await handler(request.override(args=args))
    except Exception as e:
        return unavailable(type(e).__name__)


async def main() -> None:
    # Ghi chú phiên bản: tool_name_prefix nối bằng "_" (asset_get_device), không phải "asset." —
    # tên tool của OpenAI không cho phép dấu chấm.
    client = MultiServerMCPClient(CONNECTIONS, tool_name_prefix=True, tool_interceptors=[trusted_call])
    try:
        tools = await client.get_tools()
        resources = await client.get_resources("asset", uris=["devices://catalog"])
        catalog = resources[0].data
    except Exception as e:  # server không khởi động được: agent vẫn chạy, chỉ thiếu tool tài sản
        print(f"[mcp] server 'asset' unavailable lúc nạp tool: {type(e).__name__}")
        tools, catalog = [], "(không có)"
    for t in tools:  # ẩn tham số danh tính khỏi model (bài 05); interceptor tự điền giá trị thật
        t.args_schema["properties"].pop("user_id", None)
        t.args_schema["required"] = [r for r in t.args_schema.get("required", []) if r != "user_id"]
    print(f"Tool từ MCP: {[t.name for t in tools]}, model thấy tham số: {[t.args_schema['properties'] for t in tools]}")
    print(f"Resource devices://catalog: {catalog}")

    agent = create_agent(model=llm(), tools=tools, context_schema=RequestContext, system_prompt=(
        f"Bạn là trợ lý IT Helpdesk. Trả lời ngắn gọn. Danh mục thiết bị: {catalog} "
        "Nếu tool báo unavailable thì nói hệ thống tài sản đang gián đoạn, không đoán."))

    for user, question in [("an", "Laptop của tôi là máy gì, mua khi nào, đã tới hạn đổi chưa?"),
                           ("an", "Cho tôi xem thiết bị của chi.")]:
        print(f"\n>>> [{user}] {question}")
        ctx = RequestContext(user_id=user, role=EMPLOYEES[user]["role"])
        result = await agent.ainvoke({"messages": [{"role": "user", "content": question}]},
                                     {"recursion_limit": 2 * MAX_STEPS}, context=ctx)
        for m in result["messages"]:
            if m.type == "tool":
                print(f"  tool trả: {m.content}")
        print(f"  trả lời: {result['messages'][-1].text}")


asyncio.run(main())
