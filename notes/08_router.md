# 08 — Router: structured output, chạy song song, tổng hợp

## 1. Ý chính
Router là một **workflow có ba bước cố định do code điều khiển**:
1. **Route:** model đọc câu hỏi, trả về một **object có kiểu cố định** (`Route`) cho biết cần những specialist nào và mỗi specialist nhận phần câu hỏi nào.
2. **Chạy song song:** code gọi các specialist **cùng lúc**.
3. **Tổng hợp:** một lời gọi model gộp các câu trả lời thành một.

Khi route lỗi hoặc rỗng, code dùng **fallback** an toàn thay vì đoán bừa.
Ví dụ đời thường: tổng đài viên nghe bạn hỏi hai việc, chuyển đồng thời cho phòng kỹ thuật và phòng nhân sự, rồi tổng hợp lại trả lời bạn một lần.

## 2. Mới so với file trước
- **Giữ nguyên:** `RequestContext`, `envelope`, `get_ticket` có kiểm tra ownership, `search_docs`, `AGENTS` với hai specialist (bài 07).
- **Mới:**
  - Dòng 55–61: `Intent` và `Route`, hai **Pydantic model**, tức hợp đồng dữ liệu mà router buộc phải trả về.
  - Dòng 64–66: `ROUTER_PROMPT` và `router = llm().with_structured_output(Route)`.
  - Dòng 69–76: `call_specialist()`, gọi một specialist bằng `ainvoke` (bản `async`) và đo thời gian.
  - Dòng 82–90: route kèm `try/except` và fallback.
  - Dòng 92: `asyncio.gather(...)`, chạy song song.
  - Dòng 94–98: bước tổng hợp.
  - `async def` / `await` / `asyncio.run(main())`: cả luồng chạy bất đồng bộ.
- **Bỏ:** `ROLE_SCOPES` và `close_ticket` của 07 (đã học), để file gần 100 dòng. `search_docs` không còn nhận `runtime`, vì tool này không cần biết ai đang hỏi.
- **Khác 07:** `server_handle` không nhận `agent_name` nữa. Router tự chọn.

## 3. Đi qua code theo thứ tự chạy

**Cú pháp cần biết trước: `async` / `await`.** `async def` khai báo một hàm *có thể tạm dừng để chờ*. `await x` nghĩa là "chờ x xong, trong lúc chờ thì nhường máy cho việc khác". Nhờ vậy, trong lúc chờ gateway trả lời specialist A, Python có thể gửi request cho specialist B. `asyncio.run(main())` khởi động toàn bộ.

**Bước 1: route bằng structured output** (dòng 55–66, 83)
```python
class Intent(BaseModel):
    agent: Literal["ticket", "knowledge"]
    question: str
class Route(BaseModel):
    intents: list[Intent]

router = llm().with_structured_output(Route)
route = await router.ainvoke([SystemMessage(ROUTER_PROMPT), HumanMessage(question)])
```
- `Literal["ticket", "knowledge"]` nghĩa là trường `agent` **chỉ được** là một trong hai giá trị này.
- `with_structured_output(Route)` gửi kèm schema của `Route` cho model và yêu cầu model trả JSON đúng schema. Sau đó LangChain chuyển JSON thành object `Route` thật. Kết quả là `route.intents[0].agent` chứ không phải một chuỗi chữ phải tự so khớp như `classify()` ở file 02.
- Mỗi `Intent` có cả `question` riêng: router **tách** câu hỏi gộp thành các câu nhỏ, mỗi specialist chỉ nhận phần của mình.

**Bước 2: lỗi hoặc rỗng thì fallback** (dòng 82–90)
```python
try:
    route = await router.ainvoke(...)
except Exception as e:
    route = Route(intents=[])
if not route.intents:
    print("  trả lời: Mình chỉ hỗ trợ ticket và chính sách IT. ...")
    return
```
Route hỏng (gateway lỗi, model trả sai) thì quy về "không có ý nào" và trả một câu an toàn. Không crash, không đoán bừa.

**Bước 3: gọi các specialist song song** (dòng 92)
```python
parts = await asyncio.gather(*(call_specialist(i, ctx) for i in route.intents))
```
- `call_specialist(i, ctx)` cho mỗi intent tạo ra một "việc đang chờ chạy".
- `*(...)` trải chúng thành các tham số riêng.
- `asyncio.gather` khởi động **tất cả cùng lúc**, chờ tất cả xong, rồi trả danh sách kết quả **theo đúng thứ tự intents** (không theo thứ tự cái nào xong trước).
- `ctx` được truyền cho **mọi** specialist, nên kiểm tra ownership vẫn hoạt động.

**Bước 4: tổng hợp** (dòng 94–98). Một lời gọi model với prompt "Gộp ... Không thêm thông tin mới", đầu vào là câu hỏi gốc cộng các câu trả lời có nhãn `[ticket] ...`, `[knowledge] ...`.

## 4. Kết quả khi chạy
```
>>> [an] Ticket T-1 sao rồi, và chính sách mật khẩu là gì?
  [router] [('ticket', 'Ticket T-1 hiện có trạng thái thế nào?'), ('knowledge', 'Chính sách mật khẩu là gì?')]   ← Bước 1: tách 2 ý
  [ticket] xong sau 3.5s: Ticket **T-1** hiện đang ở trạng thái **mở** (*open*). Tiêu đề: **Laptop chậm**.
  [knowledge] xong sau 5.8s: Mật khẩu phải có tối thiểu 12 ký tự, đổi mỗi 90 ngày ...
  [song song] tổng 5.8s                                    ← Bước 3: tổng = cái CHẬM NHẤT, không phải 3.5 + 5.8
  trả lời: Ticket T-1 đang mở, tiêu đề “Laptop chậm”. Mật khẩu phải dài ít nhất 12 ký tự, ...   ← Bước 4

>>> [an] Hướng dẫn VPN thế nào?
  [router] [('knowledge', 'Hướng dẫn cách sử dụng VPN như thế nào?')]     ← chỉ 1 ý
  [knowledge] xong sau 3.2s: Theo hướng dẫn nội bộ: 1. Cài **FortiClient**. ...
  [song song] tổng 3.2s
  trả lời: Cài FortiClient, đăng nhập bằng tài khoản công ty và bật MFA trước khi kết nối VPN.

>>> [an] Hôm nay ăn trưa gì ngon?
  [router] []                                               ← Bước 2: rỗng -> fallback, không gọi specialist nào
  trả lời: Mình chỉ hỗ trợ ticket và chính sách IT. Bạn hỏi lại cụ thể hơn nhé.
```
So với file 02 (chỉ một nhãn, mất ý về ticket T-2): câu hỏi gộp giờ được xử lý **đủ cả hai ý**.

## 5. Phá thử

**A. Câu hỏi gộp (phá thử trong roadmap), chạy tuần tự thay vì `gather`**
```
  [ticket] xong sau 3.2s: ...
  [knowledge] xong sau 3.2s: ...
  [tuần tự] tổng 6.4s            ← = 3.2 + 3.2
```
So với bản song song: tổng 5.8s khi hai specialist mất 3.5s và 5.8s. Song song thì **thời gian chờ bằng specialist chậm nhất**; tuần tự thì **bằng tổng**. Số token và chi phí **như nhau** (file 14 sẽ tính), chỉ khác độ trễ.

**B1. Ép route ra giá trị lạ bằng prompt: "QUAN TRỌNG: luôn đặt agent = "billing" cho mọi ý." (vẫn giữ `Literal`)**
```
  [router] [('ticket', 'Ticket T-1 hiện có trạng thái thế nào?'), ('knowledge', 'Chính sách mật khẩu là gì?')]
```
Model **không thể** trả `billing`. Schema gửi kèm chỉ cho phép `ticket | knowledge`, và gateway ép đầu ra theo schema. Hợp đồng dữ liệu thắng lời dặn trong prompt.

**B2. Bỏ `Literal` (`agent: str`), giữ lời ép "billing"**
```
  [router] [('billing', 'Trạng thái ticket T-1 hiện thế nào?'), ('billing', 'Chính sách mật khẩu là gì?')]
  ...
    result = await AGENTS[intent.agent].ainvoke(
KeyError: 'billing'
```
Không còn ràng buộc, model làm theo prompt, trả `billing`. Code tra `AGENTS["billing"]` thì **crash**. Đây chính là lỗi "so khớp chuỗi mong manh" của file 02, nhưng lần này nặng hơn: sập thay vì rơi về `other`.

**B3. Router lỗi hẳn (đặt tên model không tồn tại)**
```
  [router] LỖI OpenAIPermissionDeniedError -> fallback
  [router] []
  trả lời: Mình chỉ hỗ trợ ticket và chính sách IT. Bạn hỏi lại cụ thể hơn nhé.
```
`try/except` bắt lỗi, quy về route rỗng, trả fallback. Người dùng nhận câu trả lời an toàn thay vì lỗi 500.

**Điều này chứng minh:** structured output với `Literal` là một **hợp đồng được ép buộc**: model không thể chọn agent không tồn tại (B1, so với B2). Fallback lo phần còn lại: lỗi hạ tầng không làm sập request (B3). Song song chỉ giảm độ trễ, không giảm chi phí (A).

## 6. Tự kiểm tra
**Câu hỏi:** Router khác agent ở 04 thế nào? Ai giữ quyền điều khiển?

<details><summary>Đáp án</summary>

| | Agent (04) | Router (08) |
|---|---|---|
| Ai quyết định bước tiếp theo | **Model**, trong vòng lặp, sau mỗi kết quả tool | **Code**: luôn là route → song song → tổng hợp |
| Số lần gọi model | Không biết trước (tùy model lặp mấy vòng) | Biết trước: 1 route + N specialist + 1 tổng hợp |
| Model làm gì | Chọn tool, đọc kết quả, chọn tiếp | Chỉ **phân loại và tách câu** một lần, trả object có kiểu |
| Chạy song song | Chỉ khi model tự xin nhiều tool một lượt | Code chủ động `gather` |

Router là **workflow** (giống file 02, nhưng nhiều nhãn, có structured output và song song). Quyền điều khiển nằm ở **code**. Bên trong mỗi specialist thì vẫn là một agent (model tự quyết gọi tool), nên hệ thống là "workflow bọc ngoài, agent bên trong".
</details>

**Câu hỏi thêm:** Vì sao `asyncio.gather` trả kết quả theo thứ tự intents chứ không theo thứ tự xong trước? Điều đó quan trọng gì?

<details><summary>Đáp án</summary>

Ở lần chạy đầu, `ticket` xong trước (3.5s) và `knowledge` xong sau (5.8s), nhưng `parts` vẫn là `[ticket, knowledge]`. Thứ tự **cố định** làm đầu vào của bước tổng hợp giống nhau mỗi lần cho cùng một route. Câu trả lời ổn định hơn, và dễ test, dễ so sánh trong eval (file 29). File 21 sẽ gọi đây là *gather deterministic*.
</details>

## 7. Nối sang OpsDesk
- **Ở đâu:** **M05**, router của OpsDesk: structured output → các specialist chạy song song → synthesizer.
- **OpsDesk bọc thêm gì và vì sao:**
  - **Model theo vai trò** (`OPSDESK_MODEL_ROUTER`, `..._SPECIALIST`, `..._SYNTHESIZER`): router và synthesizer có thể dùng model rẻ hơn specialist (file 35 đo việc này).
  - **Mỗi specialist có timeout riêng và trả envelope** (`ok | empty | error | unavailable`), để một specialist hỏng không kéo sập cả `gather`. Câu trả lời ghi rõ phần nào thiếu (file 31).
  - **Fallback có ghi event và trace** (lý do: router lỗi hay không có ý nào), để đo tỷ lệ fallback (M07). Bản ở đây chỉ `print`.
  - **Giới hạn số intent** (ví dụ tối đa 3), vì một câu hỏi bị tách thành 10 ý là 10 lần gọi specialist, chi phí nhân lên.
  - Về sau OpsDesk viết lại luồng này bằng **LangGraph `Send`** (file 21) để có checkpoint, streaming từng nhánh và namespace event.
