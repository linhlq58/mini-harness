# File dùng chung duy nhất: tạo model + dữ liệu mẫu tí hon (IT Helpdesk).
import os
import sys

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()  # đọc OPENAI_BASE_URL, OPENAI_API_KEY, MODEL từ .env
sys.stdout.reconfigure(encoding="utf-8")  # để terminal Windows in được tiếng Việt

EMPLOYEES = {
    "an": {"role": "employee", "dept": "sales"},
    "binh": {"role": "it_staff", "dept": "it"},
    "chi": {"role": "it_manager", "dept": "it"},
}

TICKETS = {
    "T-1": {"owner": "an", "status": "open", "title": "Laptop chậm"},
    "T-2": {"owner": "binh", "status": "closed", "title": "VPN lỗi"},
    "T-3": {"owner": "an", "status": "in_progress", "title": "Xin cài Photoshop"},
    "T-4": {"owner": "chi", "status": "open", "title": "Máy in tầng 3 kẹt giấy"},
}

DOCS = [
    {"id": "pw", "title": "Chính sách mật khẩu", "groups": ["all"],
     "text": "Mật khẩu tối thiểu 12 ký tự, đổi mỗi 90 ngày, không dùng lại 5 mật khẩu gần nhất."},
    {"id": "vpn", "title": "Hướng dẫn VPN", "groups": ["all"],
     "text": "Cài FortiClient, đăng nhập bằng tài khoản công ty, bật MFA trước khi kết nối."},
    {"id": "laptop", "title": "Cấp laptop", "groups": ["all"],
     "text": "Nhân viên mới nhận laptop trong 2 ngày làm việc; đổi máy sau 3 năm."},
    {"id": "phish", "title": "Xử lý phishing", "groups": ["all"],
     "text": "Lỡ bấm link lạ: ngắt mạng, đổi mật khẩu, báo ngay đội Security."},
    {"id": "admin", "title": "Quy trình cấp quyền admin", "groups": ["it"],
     "text": "Quyền admin chỉ cấp tạm 24 giờ, cần IT manager duyệt, ghi audit."},
]


def llm(model: str | None = None) -> ChatOpenAI:
    # Không truyền temperature: model reasoning của gateway không nhận tham số này.
    return ChatOpenAI(model=model or os.getenv("MODEL", "GPT-6-Luna"))
