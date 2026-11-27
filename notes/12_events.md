# 12 — Streaming event: event riêng, che PII, hủy khi quá hạn

## 1. Ý chính
Khi agent chạy, framework phát ra **rất nhiều event gốc** (bắt đầu chain, từng mảnh chữ, bắt đầu/kết thúc tool...). Ta **không** đẩy thẳng chúng ra UI. Thay vào đó, ta **dịch** sang **event riêng của mình**, chỉ có 3 trường `{seq, kind, payload}`, chỉ giữ vài loại cần thiết, **che thông tin cá nhân** (email, số điện thoại) trước khi gửi đi, và **hủy** luồng nếu chạy quá thời hạn.
Ví dụ đời thường: phóng viên ngồi trong phòng họp (event gốc: mọi lời nói, kể cả chuyện nội bộ) nhưng bản tin phát ra (event riêng) chỉ gồm vài ý chính, đã che tên người cần giấu, và có giờ phát sóng cố định.

## 2. Mới so với file trước
- **Giữ nguyên:** `get_ticket` và `create_agent` của bài 04 (quay về agent đơn giản nhất để tập trung vào luồng event).
- **Mới:**
  - Dòng 22: kết quả tool có thêm `contact` (email + SĐT giả), để có PII mà che.
  - Dòng 28–35: regex `EMAIL`, `PHONE` và hàm `redact()`.
  - Dòng 31, 38–44: `HOLD` và `split_safe()`, che PII **khi chữ đang stream từng mảnh** (xem phá thử A để biết vì sao cần).
  - Dòng 47–56: `to_my_event()`, bộ dịch event gốc sang event riêng.
  - Dòng 59–79: `stream()`, một *async generator* phát event riêng, có `seq`, có `asyncio.timeout` để hủy.
  - Dòng 82–88: `main()` đóng vai "UI": chỉ đọc event riêng.
  - `astream_events(..., version="v2")` thay cho `invoke`.
- **Bỏ:** `run()` và vòng in `result["messages"]`. Giờ ta không chờ kết quả cuối mà nhận từng event **trong lúc** agent đang chạy.

## 3. Đi qua code theo thứ tự chạy

**Bước 1: "UI" bắt đầu nghe** (dòng 84)
```python
async for e in stream(question):
```
`stream()` là **async generator**: hàm có `yield` bên trong. Mỗi lần `yield` là đưa ra một event, rồi tạm dừng chờ UI đọc xong mới chạy tiếp. `async for` đọc từng event ngay khi nó có, không chờ cả câu trả lời.

**Bước 2: đặt hạn giờ** (dòng 62)
```python
async with asyncio.timeout(DEADLINE_S):
```
Mọi thứ bên trong khối này phải xong trong `DEADLINE_S` giây. Quá hạn thì Python **hủy** công việc đang chờ (lời gọi model, tool...) và ném `TimeoutError`. Ta bắt lỗi đó ở dòng 78–79 và phát event `cancelled`.

**Bước 3: nhận event gốc từ framework** (dòng 64–65)
```python
async for raw in agent.astream_events({...}, {...}, version="v2"):
```
Mỗi `raw` là một dict lớn: `{"event": "on_tool_end", "name": ..., "data": {...}, "run_id": ..., "metadata": ..., ...}`.

**Bước 4: dịch sang event riêng, bỏ phần lớn** (dòng 47–56)
```python
if kind == "on_tool_start":  return {"kind": "tool_start", ...}
if kind == "on_tool_end":    return {"kind": "tool_end", "payload": {..., "result": redact(...)}}
if kind == "on_chat_model_stream" and ...: return {"kind": "token", ...}
return None
```
Chỉ 3 loại được giữ. Kết quả tool được **che ngay** vì nó đến nguyên khối. Mọi loại event khác trả `None`, tức là bị bỏ.

**Bước 5: che PII trong chữ đang stream** (dòng 38–44, 68–70)
```python
safe, buf = split_safe(buf + event["payload"])
```
Chữ của model đến **từng mảnh nhỏ**. Ta gom vào `buf`, rồi chỉ gửi ra phần **cách đuôi hơn 30 ký tự** (`HOLD`) và đã che. 30 ký tự cuối được giữ lại chờ mảnh sau, phòng khi một email đang bị cắt dở. Nếu điểm cắt rơi giữa một PII, nó được dời ra sau PII đó. Hết luồng thì xả nốt phần đuôi (dòng 74–76).

**Bước 6: đánh số thứ tự** (dòng 72–73). Mỗi event được gửi đi có `seq` tăng dần. UI dùng `seq` để biết thứ tự, phát hiện mất event, và nối lại khi mạng chập chờn (file 36).

**Bước 7: kết thúc** bằng `done` (dòng 77) hoặc `cancelled` (dòng 79). UI luôn biết luồng đã **dừng hẳn** và vì sao.

## 4. Kết quả khi chạy
```
>>> Ticket T-1 sao rồi? Cho tôi liên hệ của người tạo.

[  1] tool_start: {'tool': 'get_ticket', 'args': {'ticket_id': 'T-1'}}                 ← Bước 4
[  2] tool_end: {'tool': 'get_ticket', 'result': '{"owner": "an", ..., "contact": "[EMAIL], [SĐT]"}'}   ← đã che
T-1 đang **mở**, nội dung “Laptop chậm”. Người tạo: **An** — [EMAIL], [SĐT].           ← Bước 5: token, che cả khi bị cắt mảnh
[ 18] done: None                                                                         ← Bước 7
```
- Agent sinh ra khoảng 50–60 event gốc, UI chỉ nhận **18** event riêng.
- Model **thấy** email thật (vì kết quả tool gốc gửi cho model chưa che) và **có viết** nó vào câu trả lời, nhưng người dùng chỉ thấy `[EMAIL], [SĐT]`. Che PII là việc ở **cửa ra**, không phụ thuộc model có nghe lời hay không.

## 5. Phá thử

**A. Che theo từng chunk, không gom (đây chính là lỗi ở lần chạy đầu của mình)**
```
Che từng chunk rồi nối lại: ... Người tạo là An, liên hệ: an@opsdesk.vn, 0912 345 678.
Các chunk quanh email: [' An', ', liên', ' hệ:', ' an@', 'opsdesk', '.vn,', ' 091', '2 ', '345 678']
```
Email bị cắt thành `' an@'` + `'opsdesk'` + `'.vn,'`, và SĐT thành `' 091'` + `'2 '` + `'345 678'`. Không mảnh nào **một mình** khớp regex, nên **lộ nguyên văn**. Vì vậy mới cần `split_safe` giữ lại phần đuôi. Bài học: một bộ lọc chạy đúng trên chuỗi hoàn chỉnh vẫn có thể **sai khi áp lên dữ liệu stream**.

**B. `DEADLINE_S = 2`**
```
[  1] tool_start: {'tool': 'get_ticket', 'args': {'ticket_id': 'T-1'}}
[  2] tool_end: {'tool': 'get_ticket', 'result': '...[EMAIL], [SĐT]...'}
[  3] cancelled: quá 2s
```
Sau 2 giây, lời gọi model thứ hai bị **hủy giữa chừng** (không chỉ là "ngừng in"), và UI nhận một event `cancelled` rõ ràng thay vì treo mãi.

**C. Nhìn event gốc của framework**
```
Số event gốc: 61 {'on_chain_start': 4, 'on_chat_model_start': 2, 'on_chat_model_stream': 41, 'on_chat_model_end': 2,
                  'on_chain_stream': 6, 'on_chain_end': 4, 'on_tool_start': 1, 'on_tool_end': 1}
Tổng kích thước nếu gửi hết ra UI: 86942 ký tự
Số event gốc chứa email CHƯA che: 11
Có event gốc chứa nguyên system prompt: True
```
Nếu đẩy thẳng event gốc ra UI: **87 KB** cho một câu trả lời ngắn, **11 event lộ email**, và **lộ cả system prompt** (bí mật vận hành, và là gợi ý cho kẻ muốn tấn công prompt injection).

**Điều này chứng minh:** lớp dịch event là một **ranh giới bảo mật và hợp đồng**: chỉ thứ đã chọn lọc và đã che mới ra ngoài. Hủy theo hạn giờ phải là hủy **thật** (dừng công việc), và phải báo cho UI bằng một event riêng.

## 6. Tự kiểm tra
**Câu hỏi:** Vì sao không đẩy thẳng event gốc của framework ra UI?

<details><summary>Đáp án</summary>

1. **Lộ dữ liệu:** event gốc chứa nguyên input/output của mọi bước, gồm system prompt, kết quả tool chưa che PII, và cả dữ liệu đã bị chặn ở bước sau (phá thử C: 11 event lộ email, lộ system prompt).
2. **Quá nhiều và quá to:** 61 event, 87 KB cho một câu ngắn. UI chỉ cần khoảng 18 event nhỏ.
3. **Hợp đồng ổn định:** event gốc thay đổi theo phiên bản framework (bản đang cài đã có `v3` bên cạnh `v2`). Nếu UI phụ thuộc vào đó, nâng cấp LangChain là hỏng UI. Event riêng `{seq, kind, payload}` là hợp đồng **mình** kiểm soát. Đổi framework thì chỉ sửa `to_my_event()`.
4. **Thêm được thứ framework không có:** `seq` để sắp thứ tự và nối lại, `done` / `cancelled` để báo kết thúc, che PII xuyên qua ranh giới chunk.
</details>

**Câu hỏi thêm:** Che PII ở event ra UI là đủ chưa? Model vẫn thấy email thật mà.

<details><summary>Đáp án</summary>

Chưa đủ cho mọi trường hợp. Ở đây model thấy email vì tool trả nguyên văn cho model. Nếu model **không cần** email để làm việc, tốt nhất tool **không trả** nó ngay từ đầu (giống bài 06: dữ liệu không cần thì không ra khỏi tool). Ngoài ra, trace (file 13) và log cũng phải che. Che ở event là **lớp cuối** trước người dùng, không thay cho việc **tối thiểu hóa dữ liệu** ở các lớp trước.
</details>

## 7. Nối sang OpsDesk
- **Ở đâu:** **M02** (định nghĩa kiểu event riêng và hợp đồng `seq/kind/payload`) và **M04** (API stream event này ra trình duyệt qua SSE, file 36).
- **OpsDesk bọc thêm gì và vì sao:**
  - **Event có type** (Pydantic, `kind` là enum gồm `route`, `tool_start`, `tool_end`, `token`, `handoff`, `error`, `done`, `cancelled`...) kèm `request_id`, để UI, eval (file 29) và audit đọc cùng một định dạng.
  - **Redaction tập trung** với nhiều mẫu hơn (số CMND, số thẻ, token API) và **có test**, đặc biệt test trường hợp PII bị cắt qua nhiều chunk như phá thử A.
  - **Hủy theo yêu cầu người dùng** (nút "Dừng" trên UI, hoặc trình duyệt ngắt kết nối), không chỉ theo hạn giờ. Cả hai cùng đi một đường hủy.
  - **Log event lại** để dựng `AgentResult` cho eval (file 29) và để nối lại luồng theo `seq` khi mất kết nối.
  - **Không bao giờ gửi event gốc** ra ngoài tầng agent. Import-linter bảo đảm tầng API chỉ thấy kiểu event riêng.
