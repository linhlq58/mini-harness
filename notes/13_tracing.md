# 13 — Tracing với LangSmith: metadata, phân loại lỗi, regression case

## 1. Ý chính
**Trace** là bản ghi chi tiết của **một lượt chạy**: model được gọi mấy lần, với input gì, tool nào chạy, kết quả gì, lỗi ở đâu, mất bao lâu, tốn bao nhiêu token. Mỗi bước là một **span** (một nút trong cây). LangSmith tự ghi trace cho mọi agent LangChain chỉ bằng biến môi trường. Ta gắn thêm **metadata/tags** (ai hỏi, loại việc) để lọc được trace. Khi có lỗi, ta **đọc trace để phân loại** (business, policy, transient hay do model), rồi biến lỗi đó thành một **regression case** để eval chạy lại mãi về sau.
Ví dụ đời thường: hộp đen máy bay. Bình thường không ai mở ra xem, nhưng khi có sự cố thì đó là nơi duy nhất biết chính xác chuyện gì đã xảy ra, theo thứ tự nào.

## 2. Mới so với file trước
- **Giữ nguyên từ bài 06:** `RequestContext`, `envelope`, `get_ticket` có kiểm tra ownership, `server_handle(...)`.
- **Mới:**
  - `.env`: `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_ENDPOINT` (APAC), `LANGSMITH_AGENT_ID` / `LANGSMITH_AGENT_ENVIRONMENT`. **Không có dòng code nào "bật" tracing.**
  - Dòng 22–23: `REGRESSION_CASES` và `client = Client()` (để đọc lại trace).
  - Dòng 39–40: lỗi hạ tầng **cố ý** khi hỏi T-3.
  - Dòng 55–57: `run_id` tự đặt, `run_name`, `metadata`, `tags` trong `config`.
  - Dòng 59–63: `try/except` quanh `invoke`, vì `create_agent` để exception của tool làm sập cả lượt.
  - Dòng 67–72: `classify()` đọc **span tool trong trace** và phân loại.
  - Dòng 75–85: `inspect_trace()` truy vấn LangSmith, phân loại, ghi regression case.
  - Dòng 90: `wait_for_all_tracers()`.
  - Dòng 17–19: ghi chú phiên bản (API đọc trace cũ bị deprecated).
- **Bỏ:** `list_my_tickets` (không cần cho bài này).

## 3. Đi qua code theo thứ tự chạy

**Bước 0: tracing bật bằng môi trường** (dòng 23 và `.env`). `common.py` gọi `load_dotenv()`. Thấy `LANGSMITH_TRACING=true`, LangChain tự gắn một "người ghi chép" vào **mọi** lần chạy, rồi gửi trace lên LangSmith **ở luồng nền** (không làm chậm câu trả lời). Hai biến `LANGSMITH_AGENT_ID=mini-harness` và `LANGSMITH_AGENT_ENVIRONMENT=local` làm trace rơi vào project **`mini-harness-local`** trên LangSmith.

**Bước 1: gắn nhãn cho lượt chạy** (dòng 55–57)
```python
run_id = uuid.uuid4()
config = {"run_id": run_id, "run_name": "helpdesk_chat", ...,
          "metadata": {"user": session_user, "workload": "chat"}, "tags": ["mini-harness", "13_tracing"]}
```
- `run_id`: **tự đặt mã** cho trace, để lát nữa tìm lại đúng nó (không phải lục trong hàng nghìn trace).
- `run_name`: tên hiển thị của nút gốc (mặc định là "LangGraph", khó phân biệt).
- `metadata`: các cặp khóa/giá trị để **lọc**, ví dụ "mọi trace của user an", "mọi trace workload chat".
- `tags`: nhãn ngắn để nhóm trace.

**Bước 2: chạy agent; T-3 làm tool ném exception** (dòng 39–40, 59–63). Agent sập, `except` bắt và in lỗi. Trace **vẫn được ghi**, kèm span lỗi.

**Bước 3: chờ trace lên hết** (dòng 90). `wait_for_all_tracers()` chờ luồng nền gửi xong. Không có dòng này, chương trình có thể thoát trước khi trace kịp gửi đi.

**Bước 4: đọc lại trace từ LangSmith** (dòng 75–80)
```python
tool_runs = list(client.list_runs(trace_id=run_id, run_type="tool"))
```
Lấy đúng các span loại `tool` trong trace có mã `run_id`. Có vòng thử lại 15 lần, vì server cần vài giây để xử lý trace vừa nhận.

**Bước 5: phân loại từ span** (dòng 67–72)
```python
if tool_run.error:  return "transient" if "ConnectionError" in ... else "unknown"
status = json.loads(tool_run.outputs["output"]["content"])["status"]
return {"ok": "ok", "not_found": "business", "denied": "policy"}.get(status, "unknown")
```
Span có `error` nghĩa là exception, tức lỗi hạ tầng. Không có thì đọc `status` của **envelope** (bài 06) mà tool đã trả. Envelope có hình dạng cố định nên mới đọc tự động được như vậy.

**Bước 6: lỗi thì thành regression case** (dòng 84–85). Mỗi case giữ **input, user, loại lỗi, trace_id**. File 29 sẽ chạy lại các case này ở mỗi lần sửa code, để lỗi đã gặp không quay lại.

## 4. Kết quả khi chạy
```
>>> [an] Ticket T-1 sao rồi?      trả lời: Ticket T-1 đang mở, ... Tiêu đề: “Laptop chậm”.
>>> [an] Ticket T-2 sao rồi?      trả lời: Bạn không có quyền xem ticket T-2.
>>> [an] Ticket T-9 sao rồi?      trả lời: Không tìm thấy ticket T-9 trong hệ thống.
>>> [an] Ticket T-3 sao rồi?      LỖI ConnectionError: DB ticket timeout                ← Bước 2

=== Đọc lại trace từ LangSmith ===
Mở trace lỗi trên web: https://apac.smith.langchain.com/o/.../projects/p/.../r/4ed9f588-...   ← bấm vào để xem cây span
  [trace d2dc639e] get_ticket(T-1) -> ok                                               ← Bước 4–5
  [trace 00c92137] get_ticket(T-2) -> policy
  [trace 3c7fc123] get_ticket(T-9) -> business
  [trace 4ed9f588] get_ticket(T-3) -> transient

REGRESSION_CASES =                                                                    ← Bước 6
  {'user': 'an', 'input': 'Ticket T-2 sao rồi?', 'category': 'policy', 'trace_id': '00c92137-...'}
  {'user': 'an', 'input': 'Ticket T-9 sao rồi?', 'category': 'business', 'trace_id': '3c7fc123-...'}
  {'user': 'an', 'input': 'Ticket T-3 sao rồi?', 'category': 'transient', 'trace_id': '4ed9f588-...'}
```
**Bạn nên tự mở link** (đăng nhập LangSmith, project `mini-harness-local`). Bạn sẽ thấy cây span `helpdesk_chat → model → tools → get_ticket` (span cuối màu đỏ, có traceback), từng lần gọi model kèm input/output và token, và tab Metadata có `user: an`, `workload: chat`.

## 5. Phá thử

**A. Tắt tracing: `LANGSMITH_TRACING=false`, không sửa một dòng code agent nào**
```
>>> [an] Ticket T-1 sao rồi?
  trả lời: Ticket T-1 “Laptop chậm” đang mở, do An phụ trách.
=== Đọc lại trace từ LangSmith ===
  [trace ffbd661b] tìm thấy 0 span tool trên LangSmith
```
Agent chạy **y hệt**, nhưng không còn trace nào. Tracing là lớp **gắn ngoài**, bật/tắt bằng môi trường, không lẫn vào logic agent.

**B. Kiểm tra metadata/tags có thật sự nằm trong trace**
```
  [trace gốc] name: helpdesk_chat | metadata.user: an | metadata.workload: chat | tags: ['mini-harness', '13_tracing']
```
Những gì gắn trong `config` đi theo trace lên server, và dùng để lọc được trên web.

**C. Câu hỏi dễ làm model điền sai tham số**
```
>>> [an] Ticket về laptop chậm của tôi sao rồi?
  trả lời: Ticket **T-1 – Laptop chậm** vẫn đang mở ...
  [trace 409947a9] get_ticket(T-1) -> ok          ← người dùng KHÔNG nói mã; model tự ĐOÁN "T-1"

>>> [an] Ticket t1 sao rồi?
  [trace 8d6a88eb] get_ticket(T-1) -> ok          ← model chuẩn hóa "t1" thành "T-1": hợp lý

>>> [an] Ticket mã 0001 sao rồi?
  trả lời: Không tìm thấy ticket mã 0001. ...
  [trace 5a02091d] get_ticket(0001) -> business   ← mã không tồn tại: đúng là business
```
Câu đầu là điểm đáng chú ý nhất. Người dùng không đưa mã ticket, model **bịa ra** `T-1` và tình cờ trúng (vì T-1 đúng là "Laptop chậm"). Bộ phân loại tự động ghi `ok`, vì nó chỉ nhìn `status`. Nhưng đây là lỗi **do model**: nếu `an` có hai ticket về laptop, model có thể đoán nhầm mà vẫn được ghi `ok`. Chỉ người **mở trace ra đọc** (thấy câu hỏi không có mã, mà tham số lại là `T-1`) mới nhận ra.

**Điều này chứng minh:** trace cho phép **tìm lại và hiểu** một lượt chạy cụ thể sau khi nó đã xảy ra. Phân loại tự động dựa trên envelope bắt được lỗi business, policy và transient, nhưng **lỗi do model** (đoán bừa, hiểu sai) thường "trông như thành công". Loại này cần người đọc trace, hoặc eval có kiểm tra quỹ đạo (file 29).

## 6. Tự kiểm tra
**Câu hỏi:** Lỗi đó thuộc loại nào: business, policy, transient hay do model?

<details><summary>Đáp án</summary>

| Loại | Ví dụ trong bài | Dấu hiệu trong trace | Nên làm gì |
|---|---|---|---|
| **business** | T-9 không tồn tại, "0001" | span tool `status: not_found` | Trả lời đúng là "không có". Không phải lỗi hệ thống |
| **policy** | an hỏi T-2 của binh | `status: denied` | Đúng là phải chặn. Theo dõi nếu một user bị chặn nhiều (dò quyền) |
| **transient** | T-3: `ConnectionError: DB ticket timeout` | span tool có `error` / exception | **Retry** có giới hạn (file 26), báo "thử lại sau". Không đổ cho người dùng |
| **do model** | Model tự đoán `T-1` khi người dùng không nói mã | Không có lỗi! Phải so **câu hỏi** với **tham số** model gửi | Sửa prompt hoặc docstring ("không có mã thì hỏi lại"), thêm regression case, eval quỹ đạo (file 29) |

Phân loại quan trọng vì **mỗi loại xử lý khác nhau**: retry lỗi `denied` là vô ích (file 26), còn coi lỗi transient là business thì người dùng nhận câu "không có ticket" trong khi ticket vẫn tồn tại.
</details>

**Câu hỏi thêm:** Vì sao phải tự đặt `run_id` thay vì để LangSmith tự sinh?

<details><summary>Đáp án</summary>

Để **nối** trace với những thứ khác của mình. Ở đây là để `inspect_trace` tìm lại đúng trace. Trong hệ thống thật, `run_id` (hoặc `request_id`) được dùng chung cho **event** (file 12), **log**, **audit** (file 27) và **trace**, nên khi người dùng báo lỗi, chỉ cần một mã là mở được tất cả.
</details>

## 7. Nối sang OpsDesk
- **Ở đâu:** **M07**, observability: tracing LangSmith, metadata, phân loại lỗi, dataset regression.
- **OpsDesk bọc thêm gì và vì sao:**
  - **`request_id` của server dùng làm `run_id`**, gắn chung với event, log và audit, để một mã mở được mọi thứ về một request.
  - **Metadata chuẩn hóa**: `user`, `role`, `workload`, `route`, `model`, `version`, để lọc trace theo bản phát hành hoặc theo model khi so sánh chi phí (file 14, 35).
  - **Che PII trong trace** (hook xử lý input/output trước khi gửi), vì trace chứa nguyên văn mọi thứ, giống event gốc ở bài 12.
  - **Lấy mẫu (sampling)** ở production, ví dụ chỉ trace 10% lượt thành công nhưng 100% lượt lỗi, để giảm chi phí và lượng dữ liệu gửi đi.
  - **Regression case lưu thành dataset trên LangSmith** (không phải list trong RAM), và eval chạy trên dataset đó ở mỗi commit (M17, file 29).
  - **Tool không để exception lọt ra** (envelope `error`, bài 06), nên lỗi transient vừa hiện trong trace vừa không làm sập lượt chạy như ở đây.
