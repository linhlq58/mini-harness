# Khái niệm: MCP server — một dịch vụ riêng công bố tool + resource qua giao thức chuẩn; tự che PII trước khi trả.
# Layer: Tools
# Khóa học: W2 L1  ·  OpsDesk: M08
import sys

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("asset", log_level="WARNING")  # tên dịch vụ; client sẽ dùng làm tiền tố tool

DEVICES = {  # dữ liệu riêng của dịch vụ quản lý tài sản, agent không chạm trực tiếp
    "an": [{"type": "laptop", "model": "Dell Latitude 7450", "serial": "SN-DL7450-88231", "bought": "2022-09"}],
    "binh": [{"type": "laptop", "model": "Dell Latitude 7450", "serial": "SN-DL7450-10457", "bought": "2025-01"},
             {"type": "phone", "model": "iPhone 16", "serial": "SN-IP16-55902", "bought": "2025-02"}],
    "chi": [{"type": "laptop", "model": "MacBook Pro 14", "serial": "SN-MBP14-73318", "bought": "2024-06"}],
}


def mask(serial: str) -> str:
    return serial[:3] + "****" + serial[-4:]  # SN-****8231: đủ để nhận ra máy, không đủ để giả mạo


@mcp.tool()
def get_device(user_id: str) -> dict:
    """Liệt kê thiết bị IT (laptop, điện thoại) của CHÍNH người đang hỏi. Không tra được thiết bị người khác."""
    print(f"[asset-server] get_device(user_id={user_id!r})", file=sys.stderr)  # stdout dành cho giao thức
    items = DEVICES.get(user_id)
    if items is None:
        return {"status": "not_found", "data": None, "safe_message": "Không có thiết bị nào."}
    masked = [d | {"serial": mask(d["serial"])} for d in items]  # che TRƯỚC khi rời server
    return {"status": "ok", "owner": user_id, "data": masked}  # ghi rõ dữ liệu này là của ai


@mcp.resource("devices://catalog")
def catalog() -> str:
    """Danh mục cấu hình chuẩn và chu kỳ đổi máy."""
    return "Văn phòng: Dell Latitude 7450. Design: MacBook Pro 14. Chu kỳ đổi laptop: 3 năm kể từ ngày mua."


if __name__ == "__main__":
    mcp.run()  # mặc định transport stdio: client khởi động tiến trình này và nói chuyện qua stdin/stdout
