# 09 — Subagent: agent gọi agent như một tool

## 1. Ý chính
Subagent là một agent **được bọc thành tool** để agent khác gọi. Agent chính viết một câu hỏi, agent con tự chạy vòng lặp **riêng** của nó (gọi tool, đọc kết quả...), rồi chỉ trả về **câu trả lời cuối**. Agent chính không thấy agent con đã làm những gì bên trong. Quyền trả lời người dùng vẫn nằm ở agent chính.
Ví dụ đời thường: sếp nhắn hỏi phòng pháp chế "hợp đồng này có rủi ro gì?". Pháp chế tự lục hồ sơ, họp nội bộ, rồi gửi lại một bản tóm tắt. Sếp đọc bản tóm tắt chứ không đọc hết biên bản họp.

## 2. Mới so với file trước
- **Giữ nguyên:** `RequestContext`, `envelope`, `get_ticket` (ownership), `search_docs`, specialist knowledge với system prompt cũ (dòng 43–44), phần in kết quả kiểu 07.
- **Mới:**
  - Dòng 47–55: tool `ask_knowledge(question)`. **Thân tool là một lời gọi agent khác.**
  - Dòng 59–64: `main_agent` với tools `[get_ticket, ask_knowledge]`.
  - Dòng 54 và 73: in danh sách message của từng agent, để thấy hai hội thoại tách biệt.
- **Bỏ so với 08:** router, `asyncio`, bước tổng hợp. Giờ **model của agent chính** tự quyết khi nào hỏi agent con (giống agent ở 04), không còn là code quyết định như router.

## 3. Đi qua code theo thứ tự chạy

**Bước 1: server gọi agent chính** (dòng 68–72). Giống 07, có `context=ctx`.

**Bước 2: agent chính đọc câu hỏi và chọn tool.** Nó thấy hai tool cùng loại: `get_ticket` và `ask_knowledge`. Với nó, `ask_knowledge` chỉ là một tool có docstring "Hỏi chuyên gia chính sách IT ...". Nó **không biết** bên trong là một agent.

**Bước 3: tool `ask_knowledge` chạy agent con** (dòng 51–52)
```python
result = knowledge_agent.invoke({"messages": [{"role": "user", "content": question}]}, ...)
```
Agent con bắt đầu một **hội thoại mới hoàn toàn**: chỉ có đúng một câu `question` mà agent chính đã viết. Nó không thấy câu hỏi gốc của người dùng, không thấy kết quả `get_ticket`, và không có `ctx` (không truyền `context=`).

**Bước 4: agent con tự làm việc.** Nó gọi `search_docs`, đọc kết quả, rồi trả lời. Toàn bộ nằm trong `inner` (dòng 53).

**Bước 5: chỉ câu cuối đi ngược lên** (dòng 55)
```python
return inner[-1].text
```
`inner[-1]` là message cuối, tức câu trả lời của agent con. Các message còn lại (lời gọi `search_docs`, nội dung tài liệu) **bị bỏ lại**.

**Bước 6: agent chính nhận kết quả như mọi tool khác**, gộp với kết quả `get_ticket`, rồi trả lời người dùng.

## 4. Kết quả khi chạy
```
>>> [an] Ticket T-1 sao rồi, và mật khẩu phải dài bao nhiêu ký tự?
  [subagent] nhận: Theo chính sách IT hiện hành, mật khẩu phải dài tối thiểu bao nhiêu ký tự?   ← Bước 3: agent chính TỰ VIẾT lại câu hỏi
  [subagent] nội bộ có 4 messages: ['human', 'ai', 'tool', 'ai']                       ← Bước 4: vòng lặp riêng của agent con
  [agent chính] có 5 messages: ['human', 'ai', 'tool', 'tool', 'ai']                   ← không có message nào của agent con
  agent chính xin gọi get_ticket({'ticket_id': 'T-1'})
  agent chính xin gọi ask_knowledge({'question': 'Theo chính sách IT hiện hành, ...'})   ← Bước 2: 2 tool cùng lượt
  agent chính nhận -> {"status": "ok", "data": {"owner": "an", ...}}
  agent chính nhận -> Theo chính sách IT hiện hành, mật khẩu phải dài tối thiểu **12 ký tự**.   ← Bước 5: chỉ 1 câu
  trả lời: Ticket T-1 đang **mở**, ...; nội dung: laptop chậm. Mật khẩu cần dài tối thiểu **12 ký tự**.
```
Hai điều cần thấy:
- Agent con có 4 message, nhưng trong 5 message của agent chính chỉ có **một** `tool` đến từ nó: câu trả lời cuối.
- Agent chính **không chuyển nguyên văn** câu của người dùng mà **viết lại** ("Theo chính sách IT hiện hành, ..."). Câu hỏi viết lại đó là **tất cả** những gì agent con biết.

## 5. Phá thử: subagent trả về toàn bộ hội thoại nội bộ thay vì câu cuối
Đổi dòng 55 thành `return json.dumps([... mọi message trong inner ...])` rồi đo `input_tokens` của agent chính:
```
Bản gốc (chỉ câu cuối):
  [token] input_tokens của agent chính mỗi lượt: [145, 288]
  agent chính nhận -> Theo chính sách IT, mật khẩu phải dài tối thiểu **12 ký tự**.

Bản trả cả hội thoại:
  [token] input_tokens của agent chính mỗi lượt: [145, 650]
  agent chính nhận -> [{"type": "human", "content": "Chính sách mật khẩu ..."}, {"type": "ai", "content": [{"arguments": ..., "call_id": "call_EU3B...", ...
  trả lời: Ticket **T-1** đang mở, ... Mật khẩu cần tối thiểu **12 ký tự**.
```
- **Câu trả lời cuối giống hệt nhau**, nhưng lượt thứ hai của agent chính tốn **650 token thay vì 288** (gấp 2,3 lần).
- Agent chính phải đọc cả mã `call_id`, JSON tham số, toàn văn tài liệu: toàn những thứ nó không cần.
- Đây mới là agent con chạy 1 vòng với 1 tài liệu ngắn. Agent con thật có thể chạy 10 vòng và đọc 20 tài liệu.

**Điều này chứng minh:** giá trị chính của subagent là **cô lập context**. Phần việc lộn xộn nằm gọn trong agent con, agent chính chỉ nhận bản tóm tắt. Context của agent chính vì vậy ngắn, rẻ và tập trung.

## 6. Tự kiểm tra
**Câu hỏi:** Agent chính thấy gì từ subagent, toàn bộ hội thoại hay chỉ kết quả?

<details><summary>Đáp án</summary>

**Chỉ kết quả**, cụ thể là cái mà tool `ask_knowledge` `return` (dòng 55: `inner[-1].text`). Danh sách message của agent chính chỉ có thêm một `ToolMessage` chứa câu đó. Chiều ngược lại cũng vậy: agent con **chỉ thấy câu hỏi agent chính viết cho nó**, không thấy câu gốc của người dùng hay kết quả các tool khác. Hai hệ quả:
1. **Ưu điểm:** context của agent chính gọn (phá thử: 288 so với 650 token), và agent con tập trung vào đúng một việc.
2. **Rủi ro:** nếu agent chính viết câu hỏi **thiếu thông tin** (ví dụ chỉ viết "cái đó có đúng không?"), agent con không có cách nào biết "cái đó" là gì. Docstring của `ask_knowledge` vì vậy dặn "Truyền một câu hỏi đầy đủ".
</details>

**Câu hỏi thêm:** Agent con có `RequestContext` không? Điều đó ổn chứ?

<details><summary>Đáp án</summary>

Không. `ask_knowledge` gọi `knowledge_agent.invoke(...)` mà không truyền `context=`. Ở đây ổn, vì `search_docs` không cần biết ai đang hỏi. Nhưng nếu agent con có tool cần quyền (ví dụ tài liệu chỉ dành cho nhóm IT, file 17), tool `ask_knowledge` phải nhận `runtime` và **chuyển tiếp** `context=runtime.context` cho agent con. Tuyệt đối không để agent chính viết "người hỏi là chi" vào câu hỏi (bài 05).
</details>

## 7. Nối sang OpsDesk
- **Ở đâu:** **M06**, agent chính gọi specialist như tool (cùng milestone với handoff ở file 10 và skill ở file 11).
- **OpsDesk bọc thêm gì và vì sao:**
  - **Chuyển tiếp `RequestContext`** vào subagent, để kiểm tra quyền vẫn đúng ở mọi tầng.
  - **Subagent trả envelope** (`ok | empty | error`) kèm câu trả lời, không chỉ chuỗi chữ, để agent chính phân biệt "không có thông tin" với "subagent lỗi".
  - **Giới hạn riêng cho subagent** (recursion, timeout, ngân sách token), vì một agent con lặp mãi sẽ làm treo cả agent chính đang chờ nó.
  - **Event có namespace** (`main > knowledge > search_docs`, file 12, 20), để UI và trace vẫn thấy được agent con đã làm gì, dù agent chính không thấy. Cô lập context **cho model**, nhưng **không** che giấu khỏi người vận hành.

## Hỏi thêm

**H: So với router (08) thì khi nào nên dùng subagent?**

Khác biệt cốt lõi là **ai quyết định gọi specialist nào, khi nào, mấy lần**: router thì **code**, subagent thì **model của agent chính**.

**Thí nghiệm: câu hỏi có hai bước phụ thuộc nhau**: *"Vấn đề trong ticket T-1 của tôi thì chính sách công ty có cho đổi máy không?"* Phải biết T-1 nói về gì (laptop) thì mới biết tra chính sách nào.

Router (08):
```
  [router] [('ticket', 'Vấn đề trong ticket T-1 của tôi là gì?'), ('knowledge', 'Chính sách công ty có cho phép đổi máy không?')]
  [ticket] ... Ticket T-1 báo vấn đề **laptop chạy chậm**.
  [knowledge] ... Mình chưa tìm thấy tài liệu chính sách về việc đổi máy. ...
  trả lời: Ticket T-1 ghi nhận laptop chạy chậm. Mình chưa tìm thấy chính sách về đổi máy; ...
```
Router tách câu **trước khi** biết T-1 nói về laptop, rồi chạy hai nhánh **song song**. Nhánh knowledge không bao giờ biết đó là laptop, nên không tìm được tài liệu "Cấp laptop". **Trả lời thiếu.**

Subagent (09), chạy 3 lần:
```
Lần 1: agent chính gọi get_ticket + ask_knowledge CÙNG LÚC (5 messages)
       -> agent con không biết T-1 là gì, phải tự thử 3 lần search (8 messages nội bộ) mới ra "đổi máy sau 3 năm"
Lần 2: ['human', 'ai', 'tool', 'ai', 'tool', 'ai']   ← get_ticket TRƯỚC, rồi mới ask_knowledge
       [subagent] nhận: Theo chính sách công ty, ticket T-1 báo laptop chậm thì người dùng có được đổi máy không? ...
       trả lời: Theo chính sách, laptop được đổi sau **3 năm**. Việc máy chậm chưa đủ căn cứ để đổi; ...
Lần 3: (giống lần 2) [subagent] nhận: ... trường hợp laptop chậm có được đổi máy không? ...
```
Ở 2/3 lần, agent chính **xâu chuỗi**: đọc kết quả `get_ticket`, rồi đưa chi tiết "laptop chậm" vào câu hỏi cho agent con. Cả 3 lần đều trả lời đúng. Nhưng lần 1 cho thấy **model không phải lúc nào cũng chọn cách tối ưu**: nó gọi song song và tốn thêm vòng lặp ở agent con.

**Bảng chọn:**

| Chọn **router** khi | Chọn **subagent** khi |
|---|---|
| Các ý **độc lập** nhau, chạy song song được ("T-1 sao rồi, **và** mật khẩu là gì?") | Bước sau **cần kết quả** bước trước (như thí nghiệm trên) |
| Tập specialist **cố định, ít**, phân loại rõ | Không biết trước cần gọi ai, mấy lần, theo thứ tự nào |
| Cần **dự đoán được**: số lời gọi cố định (1 + N + 1), chi phí và độ trễ biết trước, dễ eval | Chấp nhận model tự quyết, đổi lại **linh hoạt** (lần 1 và lần 2 đi hai đường khác nhau) |
| Cần **nhanh**: song song chủ động | Agent chính đang giữ một **hội thoại nhiều lượt** và chỉ thỉnh thoảng cần nhờ chuyên gia |
| Muốn code kiểm soát luồng (dễ thêm guard, fallback, approval giữa các bước) | Muốn **cô lập context**: việc lộn xộn của chuyên gia không làm phình context của agent chính |

**Quy tắc ngón tay cái** (giống đáp án câu tự kiểm tra của file 02): bắt đầu bằng **router** (ít tự chủ, dễ kiểm soát). Chỉ chuyển sang **subagent** khi gặp đúng loại câu hỏi mà router làm sai, tức các bước phụ thuộc nhau. Trong thực tế hai cách thường **kết hợp**: router ở ngoài cùng chọn nhánh, bên trong một nhánh là agent có subagent.
