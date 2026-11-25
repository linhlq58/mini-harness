# 03 — Agent loop tự viết tay

## 1. Ý chính
Agent là một **vòng lặp**: model đọc hội thoại rồi **đề xuất** gọi tool nào, với tham số gì. **Code** chạy tool đó, gửi kết quả trả lại cho model. Cứ lặp như vậy cho tới khi model không xin tool nữa và đưa ra câu trả lời cuối. Một giới hạn cứng `MAX_STEPS` bảo đảm vòng lặp không chạy mãi.
Ví dụ đời thường: sếp (model) viết giấy "tra giúp ticket T-1", thư ký (code) đi tra rồi mang kết quả về. Sếp đọc xong, hoặc viết thêm giấy khác, hoặc trả lời khách. Sếp không bao giờ tự đi lục tủ hồ sơ.

## 2. Mới so với file trước
- **Giữ nguyên:** `llm()`, `SystemMessage` + `HumanMessage`, hàm `run(question)`, vòng `for q in [...]` ở cuối.
- **Khác hẳn 02 ở chỗ ai quyết định:** ở 02, code chọn nhánh bằng `HANDLERS[label]`. Ở 03, **model chọn** gọi tool nào và gọi bao nhiêu lần.
- **Mới:**
  - Dòng 10: `MAX_STEPS = 5`, giới hạn cứng.
  - Dòng 13–15: `get_ticket()`, một hàm Python thường (giống `handle_ticket` ở 02, nhưng nhận đúng mã ticket thay vì tự dò bằng regex).
  - Dòng 19–30: `TOOL_SPECS`, **bản mô tả** tool dạng JSON schema để model đọc.
  - Dòng 31: `TOOLS`, bảng tên → hàm thật, do code giữ.
  - Dòng 33: `.bind_tools(TOOL_SPECS)`, gửi kèm danh sách tool trong mỗi request.
  - Dòng 42–54: vòng lặp agent.
  - `ToolMessage`: loại message mới, dùng để chứa kết quả tool.

## 3. Đi qua code theo thứ tự chạy

**Bước 1: chuẩn bị tool, gồm hai nửa tách rời** (dòng 13–33)
```python
TOOL_SPECS = [{... "name": "get_ticket", "description": "Tra trạng thái một ticket ...", "parameters": {...}}]
TOOLS = {"get_ticket": get_ticket}
model = llm().bind_tools(TOOL_SPECS)
```
- `TOOL_SPECS` là **thứ model nhìn thấy**: tên, mô tả, tham số. Model không bao giờ thấy code Python bên trong.
- `TOOLS` là **thứ code dùng** để biến tên tool thành hàm thật.
- `bind_tools` không chạy gì cả. Nó chỉ dặn rằng mỗi lần gọi model thì gửi kèm danh sách tool này.

**Bước 2: vòng lặp bắt đầu, gọi model** (dòng 42–44)
```python
for step in range(1, MAX_STEPS + 1):
    reply = model.invoke(messages)
    messages.append(reply)
```
Mỗi vòng gửi **toàn bộ** `messages` (nhớ bài 01: model không có trí nhớ). Câu trả lời của model được nối vào danh sách để vòng sau model biết chính nó vừa đề xuất gì.

**Bước 3: model trả lời luôn hay xin tool?** (dòng 45–48)
```python
if not reply.tool_calls:
    print(f"  [bước {step}] model trả lời: {reply.text}")
    return
```
`reply.tool_calls` là danh sách các đề xuất gọi tool. Danh sách rỗng nghĩa là model đã đủ thông tin và đây là câu trả lời cuối, nên thoát vòng lặp. (`reply.text` lấy phần chữ, vì khi có tool, gateway trả `content` dạng danh sách khối; xem ghi chú phiên bản ở dòng 46.)

**Bước 4: code chạy tool** (dòng 49–53)
```python
for call in reply.tool_calls:
    result = TOOLS[call["name"]](**call["args"])
    messages.append(ToolMessage(json.dumps(result, ...), tool_call_id=call["id"]))
```
- `call` có dạng `{"name": "get_ticket", "args": {"ticket_id": "T-1"}, "id": "..."}`. Đó chỉ là **dữ liệu**, một tờ giấy đề nghị.
- `TOOLS[call["name"]]` tra ra hàm thật, `(**call["args"])` gọi hàm với các tham số model đề xuất (`**` trải dict thành `ticket_id="T-1"`).
- Kết quả được bọc vào `ToolMessage` kèm `tool_call_id`, để model biết kết quả này trả lời cho đề xuất nào (quan trọng khi model xin nhiều tool một lúc).
- Rồi quay lại Bước 2: model đọc kết quả và quyết định bước tiếp theo.

**Bước 5: hết lượt** (dòng 54). Nếu chạy đủ `MAX_STEPS` vòng mà chưa có câu trả lời cuối thì dừng và báo. Code giữ "phanh", model không thể ép vòng lặp chạy tiếp.

## 4. Kết quả khi chạy
```
>>> Ticket T-1 của tôi sao rồi?
  [bước 1] model xin gọi get_ticket({'ticket_id': 'T-1'})                        ← Bước 3: có tool_calls
  [bước 1] code chạy tool -> {'owner': 'an', 'status': 'open', 'title': 'Laptop chậm'}   ← Bước 4
  [bước 2] model trả lời: Ticket T-1 **đang mở**. Nội dung: **Laptop chậm**. Hiện ticket do **An** phụ trách.   ← Bước 3: hết tool_calls

>>> So sánh trạng thái T-1 và T-2 giúp tôi.
  [bước 1] model xin gọi get_ticket({'ticket_id': 'T-1'})                        ← MỘT bước, HAI đề xuất
  [bước 1] code chạy tool -> {'owner': 'an', 'status': 'open', 'title': 'Laptop chậm'}
  [bước 1] model xin gọi get_ticket({'ticket_id': 'T-2'})
  [bước 1] code chạy tool -> {'owner': 'binh', 'status': 'closed', 'title': 'VPN lỗi'}
  [bước 2] model trả lời: - **T-1 – Laptop chậm:** Đang mở, phụ trách **An**.
- **T-2 – VPN lỗi:** Đã đóng, phụ trách **Bình**.

>>> Chào bạn!
  [bước 1] model trả lời: Chào bạn! Mình có thể giúp gì cho bạn?              ← không cần tool, trả lời luôn
```
Quan sát:
- **Model tự quyết số lần gọi tool**: 1 lần, 2 lần, hoặc không lần nào. Không có `if/else` nào trong code định trước điều đó. Câu "so sánh T-1 và T-2" mà file 02 sẽ xử lý hỏng thì ở đây chạy tốt.
- **Model hiểu sai dữ liệu**: `owner` nghĩa là *người tạo ticket*, nhưng model diễn giải thành "An **phụ trách**". Model chỉ thấy tên trường, không biết nghĩa nghiệp vụ. Tên trường và mô tả tool rõ ràng là một phần của context (file 05).

## 5. Phá thử

**A. `MAX_STEPS = 1`**
```
  [bước 1] model xin gọi get_ticket({'ticket_id': 'T-1'})
  [bước 1] code chạy tool -> {'owner': 'an', 'status': 'open', 'title': 'Laptop chậm'}
  [dừng] hết 1 bước mà chưa có câu trả lời cuối
```
Tool đã chạy và có dữ liệu, nhưng model **không còn lượt** để đọc kết quả và trả lời. Điều này cho thấy một câu hỏi dùng tool cần ít nhất 2 lần gọi model (đề xuất, rồi trả lời). Giới hạn cứng nằm trong **code**, model không vượt qua được. Đặt giới hạn quá thấp thì agent hỏng; không đặt giới hạn thì một model "kẹt" sẽ lặp mãi và đốt tiền.

**B. Tool trả về lỗi dạng dữ liệu** (`{"error": "hệ thống ticket đang bảo trì, thử lại sau 10 phút"}`)
```
  [bước 1] code chạy tool -> {'error': 'hệ thống ticket đang bảo trì, thử lại sau 10 phút'}
  [bước 2] model trả lời: Hệ thống ticket đang bảo trì. Bạn thử kiểm tra lại sau 10 phút nhé.
```
Lỗi được **gửi lại cho model như một kết quả bình thường**, và model diễn đạt nó thành câu trả lời lịch sự. Agent vẫn chạy tiếp.

**C. Tool ném exception** (`raise ConnectionError(...)`)
```
  File "...", line 51, in run
    result = TOOLS[call["name"]](**call["args"])
  File "...", line 14, in get_ticket
    raise ConnectionError("không kết nối được DB ticket")
ConnectionError: không kết nối được DB ticket
```
**Cả chương trình sập**, model không bao giờ biết chuyện gì đã xảy ra. So với B: cùng là "tool hỏng", nhưng lỗi có được bọc thành dữ liệu hay không quyết định agent sống hay chết. Đây là lý do file 06 đưa vào **result envelope** `{"status": "ok|not_found|denied", ...}`, và file 26 phân loại lỗi để retry.

**Điều này chứng minh:** model chỉ đưa ra **đề xuất dạng dữ liệu**. Mọi việc thật (chạy tool, xử lý lỗi, dừng vòng lặp) đều do code làm, và code phải chuẩn bị cho mọi tình huống.

## 6. Tự kiểm tra
**Câu hỏi:** Ai thực sự chạy tool, model hay code?

<details><summary>Đáp án</summary>

**Code.** Model chỉ trả về một đoạn dữ liệu `{"name": "get_ticket", "args": {...}}`, giống tờ giấy đề nghị. Dòng 51 `TOOLS[call["name"]](**call["args"])` mới là chỗ hàm thật được gọi. Hệ quả rất quan trọng: vì code đứng giữa, code có thể **kiểm tra trước khi chạy** (tool có tồn tại không, người dùng có quyền không: file 06, 07), **từ chối**, **ghi log**, **xin người duyệt** (file 25). Model không có cách nào tự chạm vào database. Phá thử C cũng cho thấy điều này: exception xảy ra trong tiến trình Python của bạn, không phải ở server của model.
</details>

**Câu hỏi thêm:** Vì sao phải `messages.append(reply)` trước khi thêm `ToolMessage`?

<details><summary>Đáp án</summary>

Vì `ToolMessage` là câu trả lời cho một đề xuất cụ thể (`tool_call_id`). Model (và API) cần thấy đề xuất đó nằm ngay trước trong lịch sử. Thiếu nó, API báo lỗi "tool message không khớp với lời gọi nào", hoặc model không hiểu kết quả này từ đâu ra.
</details>

## 7. Nối sang OpsDesk
- **Ở đâu:** **M03**, agent specialist đầu tiên với tool tra ticket.
- **OpsDesk bọc thêm gì và vì sao:**
  - Không tự viết vòng `while`, mà dùng `create_agent` của LangChain (file 04). Vòng lặp vẫn y hệt, chỉ là framework viết hộ, có sẵn giới hạn bước (`recursion_limit`) và streaming.
  - **Tool có type và docstring** thay cho JSON schema viết tay (file 04), để schema không bao giờ lệch so với hàm thật.
  - **Mọi tool trả về envelope** `ok | not_found | denied | error` và **không bao giờ để exception lọt ra** (file 06), vì phá thử C cho thấy một exception là sập cả request.
  - **Tool nhận `RequestContext` tin cậy** để biết ai đang hỏi (file 05), và **kiểm tra quyền sở hữu** ticket trước khi trả dữ liệu (file 06). Bản ở đây ai hỏi T-2 cũng xem được, điều không chấp nhận được trong production.
  - Mỗi bước "model xin tool / code chạy tool" thành một **event** (file 12) và một span trong **trace** (file 13), thay cho `print`.
