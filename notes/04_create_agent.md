# 04 — `create_agent` và tool có type

## 1. Ý chính
`create_agent` là **cùng vòng lặp agent của file 03**, nhưng do LangChain viết sẵn. Bạn chỉ đưa vào model, danh sách tool và system prompt. `@tool` biến một hàm Python thường thành tool: framework **tự đọc tên hàm, type hint và docstring** để sinh ra bản mô tả cho model, thay cho JSON schema viết tay.
Ví dụ đời thường: ở 03 bạn tự đi chợ, tự nấu, tự dọn. Ở 04 bạn gọi suất cơm văn phòng. Món ăn vẫn vậy, nhưng nhiều việc đã được làm hộ, và bạn cần biết đó là những việc gì.

## 2. Mới so với file trước
- **Giữ nguyên:** thân hàm `get_ticket` (dòng 15–16), `MAX_STEPS`, system prompt, hàm `run(question)`, 3 câu hỏi mẫu, cách in.
- **Mới:**
  - Dòng 12–14: `@tool` và **docstring** trên `get_ticket`. Type hint `ticket_id: str` giờ có ý nghĩa với model.
  - Dòng 20: in ra schema mà `@tool` tự sinh, để thấy nó giống `TOOL_SPECS` của 03.
  - Dòng 22–26: `create_agent(model, tools, system_prompt)`.
  - Dòng 31–34: `agent.invoke(...)` với `recursion_limit`.
- **Biến mất vào framework** (so với 03):

| File 03 (tự viết) | File 04 |
|---|---|
| `TOOL_SPECS` 12 dòng JSON schema | `@tool` + docstring |
| `TOOLS = {"get_ticket": get_ticket}` | framework tự giữ bảng tên → hàm |
| `llm().bind_tools(TOOL_SPECS)` | nằm trong `create_agent` |
| vòng `for step in range(...)` | nằm trong `create_agent` |
| `if not reply.tool_calls: return` | nằm trong `create_agent` |
| `TOOLS[call["name"]](**call["args"])` | nằm trong `create_agent` |
| `ToolMessage(json.dumps(...), tool_call_id=...)` (dòng 53 ở 03) | nằm trong `create_agent` |
| `print("[dừng] hết MAX_STEPS ...")` | `GraphRecursionError` (xem Phá thử B) |

## 3. Đi qua code theo thứ tự chạy

**Bước 1: `@tool` biến hàm thành tool** (dòng 12–20)
```python
@tool
def get_ticket(ticket_id: str) -> dict:
    """Tra trạng thái một ticket hỗ trợ IT theo mã, ví dụ T-1."""
```
`@tool` là một *decorator*: dòng `@...` đặt trên `def` để "bọc" hàm bằng thêm chức năng. Ở đây nó tạo ra một object tool, gồm:
- **tên** = tên hàm `get_ticket`,
- **mô tả** = docstring,
- **tham số** = từ type hint `ticket_id: str`.

Dòng 20 in ra đúng thứ model sẽ thấy: `{'description': 'Tra trạng thái...', 'properties': {'ticket_id': {'type': 'string'}}, 'required': ['ticket_id'], 'title': 'get_ticket'}`. Nội dung giống `TOOL_SPECS` của 03, nhưng **sinh ra từ chính hàm**, nên không thể lệch so với code thật (đổi tên tham số thì schema tự đổi theo).

**Bước 2: dựng agent** (dòng 22–26)
```python
agent = create_agent(model=llm(), tools=[get_ticket], system_prompt="...")
```
Bên trong, `create_agent` dựng một **graph LangGraph** có 2 node: `model` (gọi model) và `tools` (chạy tool), nối thành vòng: model → (có tool_calls?) → tools → model → ... Đây chính là vòng `for` của 03, chỉ là được vẽ thành graph (bạn sẽ tự dựng graph như vậy ở file 19).

**Bước 3: chạy** (dòng 31–34)
```python
result = agent.invoke(
    {"messages": [{"role": "user", "content": question}]},
    {"recursion_limit": 2 * MAX_STEPS},
)
```
- Đầu vào là **state** dạng dict có key `messages`. Có thể viết message dạng dict `{"role": "user", ...}` thay cho `HumanMessage(...)`.
- `recursion_limit` là giới hạn số **bước của graph**. Mỗi vòng agent tốn 2 bước (node model + node tools), nên `2 * MAX_STEPS`.

**Bước 4: đọc kết quả** (dòng 36–43). `result["messages"]` là **toàn bộ lịch sử**, đúng như danh sách `messages` mà 03 tự `append`. Ta chỉ duyệt lại để in. Chữ "framework chạy tool" thay cho "code chạy tool": người chạy vẫn là code, chỉ là code của LangChain.

## 4. Kết quả khi chạy
```
Schema model sẽ thấy: {'description': 'Tra trạng thái một ticket hỗ trợ IT theo mã, ví dụ T-1.',
  'properties': {'ticket_id': {'title': 'Ticket Id', 'type': 'string'}}, 'required': ['ticket_id'], ...}   ← Bước 1

>>> Ticket T-1 của tôi sao rồi?
  model xin gọi get_ticket({'ticket_id': 'T-1'})                                 ← node model
  framework chạy tool -> {"owner": "an", "status": "open", "title": "Laptop chậm"}   ← node tools
  model trả lời: Ticket T-1 về “Laptop chậm” đang mở và được giao cho An.         ← node model, hết tool_calls

>>> So sánh trạng thái T-1 và T-2 giúp tôi.
  model xin gọi get_ticket({'ticket_id': 'T-1'})
  model xin gọi get_ticket({'ticket_id': 'T-2'})
  framework chạy tool -> {"owner": "an", "status": "open", "title": "Laptop chậm"}
  framework chạy tool -> {"owner": "binh", "status": "closed", "title": "VPN lỗi"}
  model trả lời: - **T-1 – Laptop chậm:** Đang mở, phụ trách **An**. ...

>>> Chào bạn!
  model trả lời: Chào bạn! Mình có thể hỗ trợ gì về IT hôm nay?
```
**Hành vi giống hệt 03**, nhưng code ngắn hơn. Kết quả tool giờ in dạng JSON (`"owner"` có ngoặc kép) vì framework đã tự làm việc `json.dumps` của dòng 53 ở 03.

## 5. Phá thử

**A. Xóa docstring**
```
ValueError: Function must have a docstring if description not provided.
```
Chưa đến được model, **`@tool` đã từ chối** tạo tool. Framework coi mô tả là bắt buộc, vì không có nó thì model không biết tool để làm gì.

**A2. Docstring vô nghĩa (`"Hàm nội bộ."`) và tên khó hiểu (`fn_x7(a)`), chỉ có 1 tool**
```
  model xin gọi fn_x7({'a': 'T-1'})
  framework chạy tool -> {"owner": "an", "status": "open", "title": "Laptop chậm"}
  model trả lời: Ticket T-1 về **laptop chậm** đang ở trạng thái **đang mở**. ...
```
Vẫn chạy được, vì chỉ có một tool nên model **đoán mò** và may mắn đúng.

**A3. Hai tool cùng mơ hồ (`fn_y9` trả chính sách mật khẩu, `fn_x7` tra ticket), hỏi 3 lần**
```
Lần 1: model xin gọi fn_y9({'a': 'T-1'})  -> "Mật khẩu tối thiểu 12 ký tự..."
       model trả lời: Mình chưa lấy được trạng thái ticket T-1 ... Bạn thử lại sau nhé.
Lần 2: (y hệt lần 1: chọn sai, bỏ cuộc)
Lần 3: model xin gọi fn_y9 (sai) -> rồi thử fn_x7 -> trả lời đúng.

>>> Chính sách mật khẩu là gì?
  model trả lời: Chính sách mật khẩu thường yêu cầu mật khẩu đủ dài ... hãy xem hướng dẫn IT nội bộ ...
```
- Hỏi về ticket: **2/3 lần chọn sai tool rồi bỏ cuộc**. Lần còn lại phải thử 2 tool, tốn gấp đôi.
- Hỏi về mật khẩu: model **không gọi tool nào**, vì không biết `fn_y9` chứa chính sách. Nó trả lời bằng kiến thức chung ("thường yêu cầu..."), **sai** so với chính sách công ty (12 ký tự, 90 ngày).

**Điều này chứng minh:** model chọn tool **chỉ dựa vào tên, mô tả và tham số**. Nó không đọc thân hàm. Docstring không phải là ghi chú cho lập trình viên mà là **prompt cho model**. Đó là lý do quy tắc của repo này chỉ cho phép docstring trên hàm `@tool`.

**B. `MAX_STEPS = 1` (`recursion_limit = 2`)**
```
langgraph.errors.GraphRecursionError: Recursion limit of 2 reached without hitting a stop condition.
```
Ở 03, khi hết bước, code của mình in "[dừng]" và kết thúc nhẹ nhàng. Ở 04, framework **ném exception**. Giới hạn cứng vẫn còn, nhưng **cách xử lý khi chạm giới hạn đã đổi**: nếu dùng framework, bạn phải bắt `GraphRecursionError` rồi trả câu trả lời an toàn cho người dùng, không để request sập.

## 6. Tự kiểm tra
**Câu hỏi:** Những dòng nào của 03 đã "biến mất" vào framework?

<details><summary>Đáp án</summary>

Xem bảng ở mục 2: JSON schema viết tay (`TOOL_SPECS`), bảng `TOOLS`, `bind_tools`, vòng `for`, điều kiện dừng `if not reply.tool_calls`, dòng chạy tool `TOOLS[...](**args)`, dòng tạo `ToolMessage` có `tool_call_id`, và cách báo hết bước. **Không có gì mất đi thật sự**: mọi bước vẫn xảy ra y như 03, chỉ là nằm trong code của LangChain. Vì đã tự viết 03, bạn biết khi agent hỏng thì nên nghi chỗ nào: model chọn sai tool (docstring), tool lỗi (exception), hay chạm giới hạn bước (`GraphRecursionError`).
</details>

**Câu hỏi thêm:** Đổi tên tham số `ticket_id` thành `ma_ticket` trong hàm thì có phải sửa gì khác không?

<details><summary>Đáp án</summary>

Không. `@tool` sinh lại schema từ hàm, nên model sẽ thấy `ma_ticket`. Ở 03 thì phải nhớ sửa cả `TOOL_SPECS`. Quên là model gửi `ticket_id` vào và hàm báo lỗi. Đây là lợi ích chính của "tool có type": **một nguồn sự thật duy nhất**.
</details>

## 7. Nối sang OpsDesk
- **Ở đâu:** **M03**. Specialist agent của OpsDesk được dựng bằng `create_agent` với các tool `@tool`.
- **OpsDesk bọc thêm gì và vì sao:**
  - **Bắt `GraphRecursionError`** và lỗi model, trả về một câu trả lời an toàn kèm event lỗi, vì phá thử B cho thấy mặc định là sập request.
  - **Docstring tool được viết như prompt**: rõ khi nào dùng, khi nào *không* dùng, tham số có định dạng gì. Phá thử A3 cho thấy docstring mơ hồ làm model chọn sai tool và trả lời sai chính sách công ty.
  - **Tool nhận context tin cậy** qua `context_schema` của `create_agent` (file 05) thay vì đọc từ chat, và **trả envelope** `ok|not_found|denied` (file 06).
  - **Middleware** của `create_agent` (tham số `middleware=`) dùng cho guard, giới hạn và HITL (file 24, 25). Đây là lý do OpsDesk chọn `create_agent` thay vì giữ vòng lặp tự viết: có sẵn chỗ gắn thêm hành vi mà không phải sửa vòng lặp.
  - Dùng `agent.stream(...)` thay cho `invoke` để đẩy từng bước ra UI theo thời gian thực (file 12, 36).
