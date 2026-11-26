# 10 — Handoff: chuyển quyền hội thoại, giữ qua nhiều lượt

## 1. Ý chính
Handoff là **chuyển hẳn quyền trả lời** sang một agent khác. Từ lúc chuyển, các lượt **sau** đó do agent mới trả lời trực tiếp với người dùng, cho tới khi có ai chuyển lại. Muốn giữ "ai đang trả lời" qua nhiều lượt thì phải **lưu nó vào state** của hội thoại, và state đó được **checkpointer** lưu lại theo `thread_id`.
Ví dụ đời thường: gọi tổng đài, lễ tân nghe "tôi bị lừa đảo" thì **nối máy** sang phòng an ninh. Từ đó bạn nói chuyện với an ninh, lễ tân không còn trong cuộc gọi. Khác với subagent (09): lễ tân **tự gọi hỏi** phòng khác rồi quay lại trả lời bạn.

## 2. Mới so với file trước
- **Giữ nguyên:** `search_docs`, `create_agent`, `MAX_STEPS`.
- **Mới:**
  - Dòng 19–20: `HandoffState`, state mặc định cộng thêm ô `active_agent`.
  - Dòng 30–37: tool `transfer_to_security`, trả về **`Command(update=...)`**: không trả dữ liệu mà **sửa state**.
  - Dòng 40–44: tool `open_incident` của security.
  - Dòng 47–54: `PROFILES`, mỗi agent = (system prompt, bộ tool).
  - Dòng 57–62: middleware `route_by_state`, chạy **trước mỗi lần gọi model** để chọn prompt và tool theo `active_agent`.
  - Dòng 68–70: `state_schema`, `middleware`, `checkpointer=InMemorySaver()`.
  - Dòng 76: `config` có `thread_id`.
  - Dòng 88–90: ba lượt **cùng một thread**, mỗi lượt chỉ gửi **một câu mới**.
- **Bỏ:** `RequestContext` và ownership (không phải trọng tâm bài này, để file gọn).
- **Khác 09:** chỉ có **một** `create_agent`. Hai "agent" helpdesk và security thực chất là hai **cấu hình** (prompt + tool) mà middleware hoán đổi.

## 3. Đi qua code theo thứ tự chạy

**Bước 1: lượt 1 vào, checkpointer tìm state của thread** (dòng 76–77)
```python
config = {"configurable": {"thread_id": thread_id}, ...}
agent.invoke({"messages": [{"role": "user", "content": text}]}, config)
```
Ta chỉ gửi **câu mới**. Checkpointer tra `thread_id = "an-1"`. Lần đầu chưa có gì, nên state bắt đầu trống.

**Bước 2: middleware chọn "agent" trước khi gọi model** (dòng 57–62)
```python
active = request.state.get("active_agent", "helpdesk")
prompt, tools = PROFILES[active]
return handler(request.override(system_message=SystemMessage(prompt), tools=tools))
```
`@wrap_model_call` bọc **mỗi** lời gọi model. Nó đọc `active_agent` từ state (chưa có thì mặc định `helpdesk`), rồi **thay** system prompt và danh sách tool trước khi chuyển tiếp (`handler(...)`). Model helpdesk chỉ thấy `search_docs` và `transfer_to_security`. Model security chỉ thấy `open_incident`. Đây vẫn là least privilege như bài 07.

**Bước 3: lượt 2, model helpdesk quyết định handoff** (dòng 30–37)
```python
return Command(update={
    "active_agent": "security",
    "messages": [ToolMessage("Đã chuyển sang đội Security.", tool_call_id=runtime.tool_call_id)],
})
```
Tool thường trả **dữ liệu** cho model đọc. Tool này trả một **lệnh sửa state**: đặt `active_agent = "security"`, và vẫn phải kèm `ToolMessage` có đúng `tool_call_id` (hợp đồng "mỗi lời gọi tool cần một kết quả" ở bài 03). `runtime.tool_call_id` cho biết mã của lời gọi hiện tại.

**Bước 4: ngay trong lượt 2, vòng lặp chạy tiếp, lần này là security.** Lần gọi model kế tiếp, middleware đọc `active_agent = "security"`, nên prompt và tool đã khác. Security mở incident và trả lời.

**Bước 5: hết lượt, checkpointer lưu state** (dòng 70). `messages` (cả lịch sử) và `active_agent` được lưu dưới khóa `"an-1"`.

**Bước 6: lượt 3, cùng thread.** Checkpointer nạp lại state cũ: lịch sử 10 message **và** `active_agent = "security"`. Middleware chọn security ngay từ lần gọi model đầu tiên. Không cần helpdesk phân loại lại.

## 4. Kết quả khi chạy
```
>>> [thread an-1] Mật khẩu phải dài tối thiểu bao nhiêu ký tự?
  [model] đang là: helpdesk                                   ← Bước 2 (2 lần gọi model: xin tool, rồi trả lời)
  [model] đang là: helpdesk
  model xin gọi [('search_docs', {...})]
  trả lời: Mật khẩu phải dài tối thiểu **12 ký tự**.
  [state] active_agent=helpdesk, tổng 4 messages trong thread

>>> [thread an-1] Tôi vừa bấm vào link lạ trong email, nó đòi nhập mật khẩu công ty.
  [model] đang là: helpdesk
  [handoff] helpdesk -> security, lý do: ... có nguy cơ phishing.   ← Bước 3
  [model] đang là: security                                  ← Bước 4: cùng lượt, đã là security
  [model] đang là: security
  model xin gọi [('transfer_to_security', ...)]
  model xin gọi [('open_incident', {'summary': '...'})]
  trả lời: Đã mở sự cố **SEC-1**. Hãy làm ngay: 1. **Đừng nhập mật khẩu** ... 4. Cho tôi biết bạn đã nhập mật khẩu hoặc mã MFA chưa.
  [state] active_agent=security, tổng 10 messages trong thread    ← Bước 5

>>> [thread an-1] Tôi lỡ nhập mật khẩu rồi. Giờ làm gì tiếp?
  [model] đang là: security                                  ← Bước 6: ngay lần gọi đầu đã là security
  trả lời: Làm ngay theo thứ tự: 1. ... **đổi mật khẩu ngay** ... 4. ... cung cấp mã sự cố **SEC-1**.
  [state] active_agent=security, tổng 12 messages trong thread
```
Lượt 3 chỉ gửi một câu "Tôi lỡ nhập mật khẩu rồi", nhưng security vẫn **nhớ** mã SEC-1 và **vẫn là người trả lời**. Cả lịch sử lẫn quyền trả lời đều đến từ checkpointer. (Các dòng `[model]` và `[handoff]` hiện trước vì được in **trong lúc** chạy; các dòng còn lại in sau khi lượt kết thúc.)

## 5. Phá thử

**A. Lượt 3 gửi với `thread_id = "an-2"` (phá thử trong roadmap)**
```
>>> [thread an-2] Tôi lỡ nhập mật khẩu rồi. Giờ làm gì tiếp?
  [handoff] helpdesk -> security, lý do: Người dùng đã nhập mật khẩu, có nguy cơ lộ thông tin đăng nhập.
  trả lời: Mình đã mở incident **SEC-2**. ...
  [state] active_agent=security, tổng 6 messages trong thread
```
Thread mới là **hội thoại mới**: không có lịch sử, `active_agent` quay về `helpdesk`. Helpdesk phải phân loại lại, handoff lại, và security **mở thêm một sự cố trùng (SEC-2)** cho cùng một vụ việc, vì nó không biết SEC-1 đã tồn tại.

**B. Bỏ checkpointer, giữ nguyên `thread_id = "an-1"`**
```
>>> [thread an-1] Tôi vừa bấm vào link lạ ...      → handoff, [state] active_agent=security, tổng 4 messages
>>> [thread an-1] Tôi lỡ nhập mật khẩu rồi. ...
  [handoff] helpdesk -> security, ...                ← lại handoff từ đầu
  trả lời: Đã mở sự cố **SEC-1**. ...
  [state] active_agent=security, tổng 6 messages     ← không cộng dồn: 4, 4, 6 thay vì 4, 10, 12
```
Không có nơi lưu thì `thread_id` vô nghĩa: mỗi lượt bắt đầu từ trống, giống hệt bài 01 ("model không có trí nhớ"), chỉ là ở cấp agent.

**Điều này chứng minh:** handoff chỉ có tác dụng **qua nhiều lượt** khi `active_agent` nằm trong **state được lưu**. `thread_id` là **chìa khóa** để tìm đúng state đó. Sai chìa (A) hoặc không có kho (B) thì handoff "quên" ngay ở lượt sau, và có thể gây hậu quả thật như mở trùng sự cố.

## 6. Tự kiểm tra
**Câu hỏi:** Subagent khác handoff ở chỗ ai trả lời lượt tiếp theo.

<details><summary>Đáp án</summary>

| | Subagent (09) | Handoff (10) |
|---|---|---|
| Ai nói chuyện với người dùng | Luôn là **agent chính** | Agent **được chuyển tới** (security) |
| Agent kia làm gì | Làm một việc, trả **kết quả** cho agent chính rồi xong | **Tiếp quản** hội thoại |
| Lượt tiếp theo | Lại vào agent chính, nó tự quyết có hỏi lại agent con không | Vào thẳng security (`active_agent` trong state) |
| Agent kia thấy gì | Chỉ câu hỏi agent chính viết cho nó | **Toàn bộ lịch sử** của thread (security đọc được lượt hỏi mật khẩu trước đó) |
| Cần lưu gì giữa các lượt | Không bắt buộc | **Bắt buộc**: `active_agent` + lịch sử, qua checkpointer |

Chọn subagent khi cần **hỏi ý kiến chuyên gia rồi quay lại**. Chọn handoff khi chuyên gia cần **dẫn dắt cả cuộc trò chuyện** (hỏi thêm, hướng dẫn từng bước, như xử lý sự cố bảo mật).
</details>

**Câu hỏi thêm:** Ở phá thử A, `an` có thể mở bao nhiêu thread tùy thích. Vậy chặn mở trùng sự cố ở đâu?

<details><summary>Đáp án</summary>

Không thể dựa vào trí nhớ của hội thoại, vì thread là thứ người dùng (hoặc UI) tạo ra tùy ý. Việc chặn trùng phải nằm ở **tool `open_incident`**, bằng dữ liệu bền vững: ví dụ tìm sự cố đang mở của cùng người dùng cùng loại trong vài giờ gần đây, hoặc dùng **idempotency key** (file 25). Nguyên tắc giống bài 06: bất biến quan trọng phải do **code ở tầng dữ liệu** bảo vệ, không phải do model "nhớ".
</details>

## 7. Nối sang OpsDesk
- **Ở đâu:** **M06**, handoff sang specialist security cho sự cố bảo mật, cùng milestone với subagent (09) và skill (11).
- **OpsDesk bọc thêm gì và vì sao:**
  - **Checkpointer bền vững** (SQLite/Postgres, file 23) thay cho `InMemorySaver`. `InMemorySaver` mất sạch khi tắt chương trình, và không dùng chung được giữa nhiều tiến trình server.
  - **`thread_id` do server tạo và gắn với user đã đăng nhập** (kiểm tra thread đó thuộc user hiện tại), để người khác không thể đoán `thread_id` mà đọc lịch sử chat của mình. Đây là ownership của bài 06, áp dụng cho chính hội thoại.
  - **Handoff có đường chuyển lại** (security xong thì trả quyền về helpdesk) và **ghi event `handoff`** (file 12), để UI hiện "Bạn đang nói chuyện với đội Security" và audit biết ai đã xử lý.
  - **Chống trùng sự cố ở tầng dữ liệu** (idempotency, file 25), vì phá thử A cho thấy chỉ dựa vào hội thoại là mở trùng.
  - **Giới hạn độ dài lịch sử** (tóm tắt hoặc cắt bớt message cũ), vì thread dài thì mỗi lượt gửi lại toàn bộ lịch sử, tốn token tăng dần (bài 01).
