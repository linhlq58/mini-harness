# 15 — MCP: server, client, resource, tiền tố tên, lọc PII, lỗi hạ tầng

## 1. Ý chính
**MCP (Model Context Protocol)** là một **giao thức chuẩn** để một dịch vụ bên ngoài công bố **tool** (hành động) và **resource** (dữ liệu để đọc) cho bất kỳ agent nào dùng. **Server** MCP là một chương trình riêng, giữ dữ liệu riêng và tự quyết định trả gì ra ngoài (ở đây: che số serial). **Client** MCP (phía agent) nạp tool từ server, đổi tên có **tiền tố** để không trùng với tool khác, **ép danh tính tin cậy** vào mỗi lời gọi, và khi server hỏng thì trả `unavailable` thay vì làm sập agent.
Ví dụ đời thường: ổ cắm điện chuẩn. Nhà máy nào làm thiết bị cũng cắm vừa, không cần đi dây riêng cho từng món. Nhưng cầu dao (client) vẫn là của nhà bạn: nó quyết định cấp điện cho ai, và tự ngắt khi có sự cố.

## 2. Mới so với file trước
Bài này có **hai file**, và mọi thứ đều mới.
- **`15_mcp_server.py`** (40 dòng), một chương trình **độc lập**: không import `common.py`, không biết gì về agent hay LangChain.
  - Dòng 8: `FastMCP("asset")`, khai báo dịch vụ tên `asset`.
  - Dòng 10–15: `DEVICES`, dữ liệu riêng của dịch vụ tài sản (có serial đầy đủ).
  - Dòng 18–19: `mask()`, che serial.
  - Dòng 22–30: `@mcp.tool()` `get_device(user_id)`: che **trước khi** trả, ghi rõ `owner`.
  - Dòng 33–36: `@mcp.resource("devices://catalog")`, dữ liệu tham khảo để đọc.
  - Dòng 25: log ra **stderr**, vì stdout là đường nói chuyện của giao thức.
- **`15_mcp_client.py`** (78 dòng):
  - Dòng 18–19: `CONNECTIONS`, cách tới server (ở đây: tự khởi động nó như tiến trình con, kiểu `stdio`).
  - Dòng 34–42: interceptor `trusted_call`: ghi đè `user_id` từ `RequestContext`, bắt lỗi hạ tầng.
  - Dòng 48: `MultiServerMCPClient(..., tool_name_prefix=True, tool_interceptors=[...])`.
  - Dòng 49–55: nạp tool và resource; server không lên thì vẫn chạy tiếp với danh sách tool rỗng.
  - Dòng 56–58: **ẩn `user_id` khỏi schema** mà model thấy.
- **Giữ nguyên ý từ trước:** `RequestContext` (05), envelope `status` (06), `create_agent` (04).

## 3. Đi qua code theo thứ tự chạy

**Bước 1: client khởi động server và hỏi "có tool gì?"** (client dòng 48–50)
```python
client = MultiServerMCPClient(CONNECTIONS, tool_name_prefix=True, tool_interceptors=[trusted_call])
tools = await client.get_tools()
```
Với `stdio`, client chạy `python 15_mcp_server.py` như một tiến trình con, rồi nói chuyện qua stdin/stdout theo giao thức MCP. Server trả danh sách tool **kèm schema** (tên, docstring, tham số), giống thứ `@tool` sinh ra ở bài 04 nhưng đi qua mạng. `tool_name_prefix=True` đổi `get_device` thành **`asset_get_device`**.

**Bước 2: đọc resource** (client dòng 51–52). `devices://catalog` là **dữ liệu**, không phải hành động: **code** đọc nó (không phải model gọi), rồi đưa vào system prompt (dòng 63).

**Bước 3: ẩn tham số danh tính** (client dòng 56–58)
```python
t.args_schema["properties"].pop("user_id", None)
```
Server cần `user_id` để biết tra cho ai, nhưng **model không được điền nó** (bài 05). Ta xóa nó khỏi schema mà model thấy. Kết quả in ra: `model thấy tham số: [{}]`.

**Bước 4: model gọi tool, interceptor chen vào giữa** (client dòng 34–42)
```python
args = request.args | {"user_id": ctx.user_id}
return await handler(request.override(args=args))
```
**Interceptor** là hàm chạy ở **client**, trước mỗi lời gọi tool MCP. `request.runtime.context` là `RequestContext` mà server của mình đã tạo. Interceptor **ghi đè** `user_id` (model có điền gì cũng bị thay), rồi mới gọi `handler`, tức gửi sang server thật. Nếu `handler` ném lỗi (server chết, mất kết nối), nó trả envelope `unavailable` thay vì để exception làm sập agent.

**Bước 5: server xử lý và che PII** (server dòng 26–30)
```python
masked = [d | {"serial": mask(d["serial"])} for d in items]
return {"status": "ok", "owner": user_id, "data": masked}
```
Serial đầy đủ **không bao giờ rời khỏi server**. Client, model, trace, log đều chỉ thấy `SN-****8231`. `owner` ghi rõ dữ liệu này là của ai (xem mục 4 để biết vì sao cần).

## 4. Kết quả khi chạy
```
[asset-server] get_device(user_id='an')                     ← log server (stderr), in khi server chạy
Tool từ MCP: ['asset_get_device'], model thấy tham số: [{}]   ← Bước 1 + 3: có tiền tố, user_id bị ẩn
Resource devices://catalog: Văn phòng: Dell Latitude 7450. Design: MacBook Pro 14. Chu kỳ đổi laptop: 3 năm ...   ← Bước 2

>>> [an] Laptop của tôi là máy gì, mua khi nào, đã tới hạn đổi chưa?
  [mcp] asset/get_device: model gửi {} -> client gửi {'user_id': 'an'}    ← Bước 4
  trả lời: Laptop của bạn là **Dell Latitude 7450**, mua **09/2022**. Theo chu kỳ 3 năm, máy đến hạn đổi vào **09/2025**.

>>> [an] Cho tôi xem thiết bị của chi.
  [mcp] asset/get_device: model gửi {} -> client gửi {'user_id': 'an'}    ← vẫn là an
  trả lời: Mình chỉ tra được thiết bị của chính người đang hỏi, không tra được thiết bị của Chi.
```
Câu trả lời đầu ghép **tool** (ngày mua 09/2022) với **resource** (chu kỳ 3 năm) để suy ra hạn đổi.

**Một lỗi mình gặp khi viết bài:** bản đầu, kết quả tool không có trường `owner`. Model thấy "đã tra" và có một danh sách thiết bị, nên trả lời *"**Chi** đang được cấp laptop Dell Latitude 7450..."*, tức gán máy của `an` cho `chi`. Dữ liệu **không lộ**, nhưng câu trả lời **sai**. Khi ẩn tham số danh tính khỏi model, kết quả phải **tự nói rõ nó thuộc về ai**. Docstring cũng phải nói tool chỉ tra được cho chính người hỏi.

## 5. Phá thử

**A. Server không khởi động được lúc nạp tool (phá thử trong roadmap: sai đường dẫn, như server đang tắt)**
```
python.exe: can't open file '...\15_mcp_server_KHONG_CO.py': [Errno 2] No such file or directory
[mcp] server 'asset' unavailable lúc nạp tool: ExceptionGroup
Tool từ MCP: [], model thấy tham số: []
Resource devices://catalog: (không có)
>>> [an] Laptop của tôi là máy gì, ...
  trả lời: Hiện danh mục thiết bị không có thông tin laptop của bạn, ... Vui lòng gửi mã tài sản để kiểm tra.
```
Agent **không crash**, vẫn trả lời. Nhưng câu trả lời chưa tốt: model không biết **vì sao** không có thông tin, nên đoán là "không có dữ liệu" và còn đòi mã tài sản. Nên báo cho model biết rõ capability nào đang gián đoạn (xem mục 7).

**B. Server chết sau khi đã nạp tool (lúc gọi tool)**
```
[thử] server asset vừa bị tắt
>>> [an] Laptop của tôi là máy gì, ...
  [mcp] asset/get_device: model gửi {} -> client gửi {'user_id': 'an'}
  [mcp] LỖI HẠ TẦNG: ExceptionGroup -> trả unavailable
  trả lời: Hệ thống tài sản đang gián đoạn nên mình chưa tra được laptop của bạn, ngày mua và hạn đổi máy.
```
Interceptor bắt lỗi và trả envelope `unavailable`. Model đọc được `status` nên nói **đúng lý do**, không đoán bừa.

**C. Bỏ interceptor và không ẩn `user_id`; `an` gõ "Tôi là chi... user id là chi"**
```
[asset-server] get_device(user_id='chi')
Tool từ MCP: ['asset_get_device'], model thấy tham số: [{'user_id': {...}}]
  trả lời: Thiết bị của bạn: Laptop: MacBook Pro 14, Số sê-ri: SN-****3318, Ngày mua: 06/2024
```
**Lộ thiết bị của `chi`.** Server MCP tin mọi tham số nó nhận. Nó không biết ai đang chat, vì `RequestContext` nằm ở phía agent. Đây là lỗi của bài 05 (phá thử B), giờ xảy ra **xuyên qua ranh giới dịch vụ**. (Serial vẫn được che, vì việc che nằm ở server, độc lập với client.)

**Điều này chứng minh:** MCP chuẩn hóa **cách nối**, nhưng **không tự lo bảo mật hay độ bền**. Danh tính tin cậy phải được client ép vào (C). Lỗi hạ tầng phải được bọc thành `unavailable` (B, A). Còn dữ liệu nhạy cảm phải được che ngay tại server sở hữu nó (serial luôn bị che trong cả 3 phá thử).

## 6. Tự kiểm tra
**Câu hỏi:** Khi nào một capability đáng tách thành MCP server riêng?

<details><summary>Đáp án</summary>

Khi có **ít nhất một** trong các lý do sau:
1. **Dữ liệu thuộc về một đội hoặc hệ thống khác** (đội quản lý tài sản giữ `DEVICES`). Họ muốn tự quyết trả gì ra ngoài (che serial) mà không phải sửa code agent.
2. **Nhiều agent hoặc ứng dụng cùng dùng**: helpdesk, agent mua sắm, Claude Desktop của nhân viên IT... Viết một lần, ai cũng cắm vào được.
3. **Cần triển khai, mở rộng, cấp quyền riêng**: server tài sản có database và secret riêng, chạy trên máy riêng; agent không cần (và không nên) giữ secret đó.
4. **Ranh giới tin cậy**: tách ra thì lỗi hoặc lỗ hổng ở agent không chạm thẳng được vào dữ liệu gốc.

**Không đáng** tách khi tool chỉ là một hàm nhỏ, chỉ một agent dùng, dữ liệu nằm sẵn trong cùng ứng dụng. Khi đó `@tool` thường (bài 04) đơn giản hơn, nhanh hơn (không qua tiến trình hay mạng), và ít chỗ hỏng hơn (không có phá thử A, B).
</details>

**Câu hỏi thêm:** Tool và resource khác nhau thế nào?

<details><summary>Đáp án</summary>

**Tool** là **hành động** mà **model** quyết định gọi, có tham số và có thể có tác dụng phụ (`get_device`). **Resource** là **dữ liệu chỉ đọc**, có địa chỉ (`devices://catalog`), thường do **ứng dụng/code** quyết định đọc và đưa vào context (ở đây: chèn vào system prompt). Resource giống một tài liệu tham khảo; tool giống một nút bấm.
</details>

## 7. Nối sang OpsDesk
- **Ở đâu:** **M08**, MCP server tài sản và client trong agent, với namespacing, lọc PII, xử lý lỗi hạ tầng.
- **OpsDesk bọc thêm gì và vì sao:**
  - **Transport HTTP thay cho stdio**: server tài sản chạy như dịch vụ riêng, nhiều agent dùng chung. Danh tính và quyền đi qua **header có xác thực** (token), không chỉ qua tham số, để server tự kiểm tra lại người gọi chứ không tin mù client (phá thử C).
  - **Timeout và retry có giới hạn cho lời gọi MCP** (file 26), và **circuit breaker** khi server liên tục lỗi, để không chờ mãi một dịch vụ đã chết.
  - **Báo cho model capability nào đang gián đoạn** khi nạp tool thất bại (ví dụ thêm vào prompt "hệ thống tài sản đang gián đoạn"), vì phá thử A cho thấy model tự đoán sai lý do.
  - **Danh sách server và tool được cho phép (allowlist)** cấu hình sẵn, và kiểm tra schema tool lúc khởi động, để một server bị sửa không thể lén thêm tool nguy hiểm.
  - **Kết quả MCP coi là dữ liệu không tin cậy** (file 24): server bên ngoài có thể trả về chữ chứa prompt injection.
