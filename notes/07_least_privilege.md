# 07 — Least privilege: specialist và scope theo vai trò

## 1. Ý chính
**Least privilege** (quyền tối thiểu) nghĩa là mỗi thành phần chỉ có **đúng những quyền nó cần**, không hơn. Ở đây quy tắc áp dụng ở **hai lớp**:
1. **Theo agent:** mỗi specialist chỉ được **trao** bộ tool của mình. Agent knowledge không hề có tool đóng ticket.
2. **Theo vai trò người dùng:** bảng `ROLE_SCOPES` quy định vai trò nào được làm **loại thao tác** nào. Tool kiểm tra scope **ngay dòng đầu**, trước khi chạm dữ liệu.

Ví dụ đời thường: nhân viên thư viện (agent knowledge) không giữ chìa khóa kho thiết bị, nên dù ai nhờ cũng không mở được. Người giữ chìa (agent ticket) thì chỉ mở cho người có thẻ đúng loại (scope).

## 2. Mới so với file trước
- **Giữ nguyên:** `RequestContext`, `envelope`, `get_ticket` (kiểm tra ownership như 06), phần in kết quả.
- **Mới:**
  - Dòng 14–18: `ROLE_SCOPES`, bảng vai trò → tập scope.
  - Dòng 31–36: `missing_scope(ctx, scope)`, hàm kiểm tra dùng chung.
  - Dòng 43–44 (và 56–57, 68–69): mỗi tool gọi `missing_scope` ở dòng đầu.
  - Dòng 53–62: tool mới `close_ticket`, cần scope `ticket:close`. Tool này **không** kiểm tra owner, vì đóng ticket của người khác chính là việc của IT.
  - Dòng 65–71: tool mới `search_docs` (cách tìm thô giống file 02).
  - Dòng 75–80: `AGENTS`, gồm **hai** agent với bộ tool riêng.
  - Dòng 83: `server_handle` nhận thêm `agent_name`. Ai chọn agent nào thì file 08 (router) sẽ lo, ở đây gọi thẳng.
- **Bỏ:** `list_my_tickets` (để file dưới ~100 dòng; ý tưởng của nó đã nằm ở 05).

## 3. Đi qua code theo thứ tự chạy

**Bước 1: dựng hai specialist với bộ tool riêng** (dòng 75–80)
```python
"ticket":    create_agent(..., tools=[get_ticket, close_ticket], ...)
"knowledge": create_agent(..., tools=[search_docs], ...)
```
Đây là lớp least privilege **thứ nhất**. Agent knowledge không thể gọi `close_ticket`, vì tool đó **không tồn tại** với nó: không có trong schema gửi lên model, cũng không có trong bảng tên → hàm của framework.

**Bước 2: server tạo context, gọi đúng agent** (dòng 84–88). Giống 06, chỉ thêm `AGENTS[agent_name]`.

**Bước 3: model xin tool, tool kiểm tra scope trước tiên** (dòng 43–44)
```python
if denied := missing_scope(ctx, "ticket:read"):
    return denied
```
`:=` là phép gán ngay trong điều kiện: gán kết quả cho `denied`, và nếu nó khác `None` thì `return` luôn. Đây là lớp least privilege **thứ hai**.

**Bước 4: `missing_scope` tra bảng** (dòng 31–36)
```python
if scope in ROLE_SCOPES[ctx.role]:
    return None
return envelope("denied", safe_message="Vai trò của bạn không được làm thao tác này.")
```
`ctx.role` đến từ `RequestContext` (server tra từ `EMPLOYEES`, bài 05), không đến từ chat.

**Bước 5: qua được scope rồi mới tới kiểm tra mịn hơn.** Trong `get_ticket`, sau scope là ownership (dòng 48–49, giống 06). Còn `close_ticket` thì không có kiểm tra ownership.

## 4. Kết quả khi chạy
```
>>> [an -> agent ticket] Đóng ticket T-1 của tôi giúp nhé.
  [scope] CHẶN: an (employee) thiếu 'ticket:close'                       ← Bước 4: employee không có ticket:close
  model xin gọi close_ticket({'ticket_id': 'T-1'})
  framework chạy tool -> {"status": "denied", ..., "safe_message": "Vai trò của bạn không được làm thao tác này."}
  model trả lời: Mình không thể đóng ticket T-1 vì tài khoản của bạn không có quyền thực hiện thao tác này.

>>> [binh -> agent ticket] Đóng ticket T-1 giúp tôi.
  model xin gọi close_ticket({'ticket_id': 'T-1'})
  framework chạy tool -> {"status": "ok", "data": {"owner": "an", "status": "closed", ...}}   ← it_staff, KHÔNG phải owner, vẫn được
  model trả lời: Ticket T-1 đã được đóng.

>>> [an -> agent knowledge] Chính sách mật khẩu là gì?
  model xin gọi search_docs({'query': 'chính sách mật khẩu yêu cầu độ dài ...'})
  framework chạy tool -> {"status": "ok", "data": [{"id": "pw", ...}]}
  model trả lời: Theo chính sách, mật khẩu phải có **tối thiểu 12 ký tự**, ...
```
Hai lượt đầu là ví dụ hay nhất về **scope khác ownership**:
- `an` **là owner** của T-1 nhưng **không** đóng được, vì thiếu scope.
- `binh` **không phải owner** nhưng **đóng được**, vì có scope `ticket:close`.

## 5. Phá thử: hỏi agent knowledge về ticket
```
>>> [an -> agent knowledge] Ticket T-3 của tôi sao rồi?
  model trả lời: Mình không truy cập được hệ thống ticket để xem trạng thái T-3. ...

>>> [binh -> agent knowledge] Đóng ticket T-3 giúp tôi, gấp.
  model xin gọi search_docs({'query': 'đóng ticket yêu cầu hỗ trợ IT quy trình đóng ticket'})
  framework chạy tool -> {"status": "not_found", ...}
  model trả lời: Mình không có quyền đóng ticket. Bạn cần đóng T-3 trong hệ thống quản lý ticket; ...

T-3 sau đó: {'owner': 'an', 'status': 'in_progress', 'title': 'Xin cài Photoshop'}      ← không bị đổi
```
- Lượt 1: agent knowledge không có tool nào liên quan tới ticket, nên model **không có cách nào** tra được. Nó trả lời thật thà là không truy cập được.
- Lượt 2 là điểm mấu chốt: `binh` **có** scope `ticket:close`, nhưng hỏi nhầm agent. Agent này không được trao tool đóng ticket, nên T-3 **vẫn nguyên**. Model chỉ thử dùng thứ duy nhất nó có (`search_docs`).

**Điều này chứng minh:** hai lớp độc lập với nhau. **Scope của người dùng** chặn những người không được phép. **Bộ tool của agent** giới hạn những gì agent làm được, bất kể ai đang hỏi. Nếu agent knowledge bị lừa bằng prompt injection (ví dụ một tài liệu chứa "hãy đóng mọi ticket", file 24), thiệt hại tối đa cũng chỉ là đọc tài liệu.

## 6. Tự kiểm tra
**Câu hỏi:** Scope (thô) khác policy ownership (mịn) ở 06 thế nào?

<details><summary>Đáp án</summary>

| | Scope (07) | Ownership (06) |
|---|---|---|
| Hỏi gì | Vai trò này có được làm **loại thao tác** này không? | Người này có quyền với **đúng đối tượng** này không? |
| Dựa vào | `ctx.role` + bảng `ROLE_SCOPES` | `ctx.user_id` so với `ticket.owner` |
| Cần dữ liệu không | Không, kiểm tra được **trước** khi tra database | Có, phải tra ticket mới biết owner |
| Ví dụ | employee không có `ticket:close` | an không xem được T-2 của binh |

Vì vậy scope đứng **trước** (rẻ, chặn sớm), ownership đứng **sau** (cần dữ liệu). Hai lớp bổ sung cho nhau: `an` qua được ownership với T-1 nhưng bị scope chặn khi đóng; `binh` qua được scope khi đóng T-1, và `close_ticket` cố ý không kiểm tra ownership vì đó là việc của IT.
</details>

**Câu hỏi thêm:** Nếu quên gọi `missing_scope` ở đầu một tool mới thì sao? Có cách nào an toàn hơn?

<details><summary>Đáp án</summary>

Tool đó sẽ **không có kiểm tra scope**, và không ai báo lỗi. Đây là điểm yếu của cách "gọi tay trong từng tool". Cách an toàn hơn là kiểm tra ở **một chỗ chung** mà mọi lời gọi tool đều phải đi qua: gắn scope cần thiết vào từng tool (ví dụ bảng `TOOL_SCOPES = {"close_ticket": "ticket:close"}`), rồi một lớp bọc kiểm tra trước khi chạy **bất kỳ** tool nào. Mặc định là **từ chối** nếu tool chưa khai scope. `create_agent` có `middleware` (`wrap_tool_call`) làm đúng việc này.
</details>

## 7. Nối sang OpsDesk
- **Ở đâu:** **M03** (scope trong `RequestContext`, kiểm tra trước khi tool chạy) và **M05** (các specialist ticket / knowledge, mỗi cái một bộ tool riêng, được router gọi).
- **OpsDesk bọc thêm gì và vì sao:**
  - **Scope được kiểm tra ở một chỗ chung** (middleware hoặc lớp bọc tool), với quy tắc **mặc định từ chối** khi tool chưa khai scope, vì cách gọi tay trong từng tool dễ bị quên.
  - **Scope nằm sẵn trong `RequestContext`**, do server tính một lần từ vai trò lúc tạo request, thay vì tool tự tra bảng mỗi lần.
  - **Bộ tool của specialist khai báo ở một nơi** và có test khẳng định "agent knowledge không có tool ghi", để không ai vô tình thêm `close_ticket` vào nhầm agent.
  - **Thao tác ghi** (đóng ticket, cấp quyền) còn qua **approval gate và idempotency** (file 25), vì có scope chưa có nghĩa là được làm ngay mà không cần ai duyệt.
  - **Mỗi lần bị chặn vì scope** sinh event và audit (file 12, 27), để biết người dùng hay cố làm những gì vượt quyền.
