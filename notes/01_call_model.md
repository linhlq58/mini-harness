# 01 — Gọi model và danh sách `messages`

## 1. Ý chính
Gọi model là **gửi một danh sách tin nhắn** (`system` / `user` / `assistant`) và nhận về **một tin nhắn mới**. Model **không có trí nhớ**: mỗi lần gọi là một lần gặp mới hoàn toàn. Muốn nó "nhớ" thì phải gửi lại cả lịch sử.
Ví dụ đời thường: giống nhắn cho một tổng đài viên mỗi lần lại là người khác. Muốn họ biết chuyện cũ thì phải dán lại cả đoạn chat.

## 2. Mới so với file trước
Đây là file đầu tiên, nên mọi thứ đều mới. Ngoài ra có `common.py` (dùng chung cho mọi file):
- `llm()` tạo `ChatOpenAI` trỏ tới gateway của khóa học. URL, key và tên model đọc từ `.env`.
- `EMPLOYEES`, `TICKETS`, `DOCS`: dữ liệu mẫu, file 01 chưa dùng tới.
- `sys.stdout.reconfigure(encoding="utf-8")`: để terminal Windows in được tiếng Việt.

## 3. Đi qua code theo thứ tự chạy

**Bước 1: tạo model** (dòng 8)
```python
model = llm()
```
Dòng này chỉ tạo một "client" biết gọi tới đâu, chưa gửi gì đi cả.

**Bước 2: dựng danh sách messages** (dòng 11–14)
```python
messages = [
    SystemMessage("Bạn là trợ lý IT Helpdesk. Trả lời ngắn gọn, tối đa 2 câu."),
    HumanMessage("Tên tôi là An. Laptop của tôi chạy rất chậm, ..."),
]
```
- `SystemMessage`: luật chơi do **lập trình viên** đặt ra (vai trò, giọng, độ dài). Người dùng không thấy tin này.
- `HumanMessage`: lời của **người dùng** (khi in ra, loại tin này tên là `human`).

**Bước 3: gọi model** (dòng 19–21)
```python
reply = model.invoke(messages)
print("usage:", reply.usage_metadata)
```
`invoke` gửi **một request HTTP** chứa cả danh sách và nhận về `AIMessage`. `usage_metadata` cho biết số token vào/ra, cũng chính là thứ bạn trả tiền (file 14 sẽ đổi ra VND).

**Bước 4: có gửi lại lịch sử** (dòng 24–26)
```python
history = messages + [AIMessage(reply.content), HumanMessage("Tên tôi là gì?")]
```
Ta tự nối câu trả lời cũ (`AIMessage`, vai `assistant`) và câu hỏi mới vào danh sách. "Trí nhớ" thực chất là **code gửi lại danh sách này**.

**Bước 5: không gửi lịch sử** (dòng 31–33)
```python
alone = [messages[0], HumanMessage("Tên tôi là gì?")]
```
Chỉ có system và câu hỏi mới, nên model không có cách nào biết tên An.

## 4. Kết quả khi chạy
```
=== Lượt 1: gửi 2 messages ===                         ← Bước 2
  [system] Bạn là trợ lý IT Helpdesk. Trả lời ngắn gọn, tối đa 2 câu.
  [human] Tên tôi là An. Laptop của tôi chạy rất chậm, tôi nên làm gì trước?

[ai] An hãy lưu công việc rồi khởi động lại laptop, sau đó đóng các ứng dụng
không cần thiết. Nếu máy vẫn chậm, hãy kiểm tra trong Task Manager ...     ← Bước 3: đúng 2 câu, theo system
usage: {'input_tokens': 51, 'output_tokens': 104, ..., 'output_token_details': {'reasoning': 43}}

=== Lượt 2a: gửi lại cả lịch sử ( 4 messages ) ===     ← Bước 4
[ai] Tên bạn là An.                                    ← "nhớ" vì tên nằm trong lịch sử gửi kèm
usage: {'input_tokens': 118, 'output_tokens': 8, ...}  ← input tăng từ 51 lên 118: lịch sử tốn token

=== Lượt 2b: chỉ gửi câu hỏi mới ( 2 messages ) ===    ← Bước 5
[ai] Tôi chưa biết tên của bạn.                        ← không có lịch sử, không có trí nhớ
usage: {'input_tokens': 37, 'output_tokens': 31, ...}
```
Hai điều đáng chú ý:
- **Lịch sử tốn tiền**: lượt 2a phải trả 118 token đầu vào, gấp 3 lần lượt 2b (37 token), chỉ để model "nhớ" thêm một cái tên. Hội thoại càng dài, mỗi lượt càng đắt.
- `reasoning: 43`: model này "suy nghĩ" ngầm trước khi trả lời. Phần suy nghĩ đó **tính vào output_tokens** dù bạn không thấy nội dung của nó.

## 5. Phá thử
Chạy bản tạm (không sửa file gốc) với cùng câu hỏi về laptop chậm:

**A. Bỏ system message**
```
[ai] An hãy bắt đầu bằng các bước an toàn, theo thứ tự này:
1. **Khởi động lại máy** ...
2. **Kiểm tra ứng dụng đang ngốn tài nguyên** ...
3. **Kiểm tra dung lượng ổ đĩa** ...
4. **Tắt ứng dụng không cần tự khởi động** ...
... An đang dùng Windows hay Mac?
output_tokens: 354
```
**B. Đổi system thành "giọng cướp biển, đúng 1 câu, cộc lốc"**
```
[ai] Arrr, An hãy khởi động lại laptop trước rồi xem máy còn chậm không.
output_tokens: 127
```
**Điều này chứng minh:** system prompt là **cần điều khiển chính** của bạn với model. Bỏ nó đi thì model trả lời dài gấp khoảng 3 lần (354 so với 104 token), dùng markdown và còn hỏi ngược lại. Đổi nó thì giọng và độ dài đổi theo ngay. Kiến thức của model vẫn vậy ("khởi động lại máy"); thứ thay đổi là **hành vi**. Ngoài ra, system prompt cũng là cách rẻ nhất để giảm chi phí.

## 6. Tự kiểm tra
**Câu hỏi:** Model có "nhớ" lượt trước không nếu bạn không gửi lại lịch sử?

<details><summary>Đáp án</summary>

Không. Mỗi `invoke` là một request độc lập; server của model không giữ gì giữa các lần gọi (lượt 2b trả lời "Tôi chưa biết tên của bạn"). "Trí nhớ" của chatbot là do **code phía bạn** lưu danh sách messages rồi gửi lại mỗi lượt. Cái giá là token đầu vào tăng dần (51 → 118). Sau này checkpointer (file 10, 22, 23) chính là nơi lưu danh sách đó một cách có tổ chức.
</details>

**Câu hỏi thêm:** Vì sao system prompt do lập trình viên viết, không để người dùng gửi?

<details><summary>Đáp án</summary>

System là kênh **tin cậy** đặt luật cho model. Nếu người dùng ghi được vào đó thì họ đổi được luật. Đây là mầm của "trust channel" ở file 05 và 24.
</details>

## 7. Nối sang OpsDesk
- **Ở đâu:** milestone **M03**, chỗ tạo model client (factory model theo vai trò: `OPSDESK_MODEL_ROUTER`, `..._SPECIALIST`, `..._SYNTHESIZER` trong `.env`).
- **OpsDesk bọc thêm gì và vì sao:**
  - **Model theo vai trò, không theo tên**: agent xin "router" chứ không xin "GPT-6-Luna". Nhờ vậy đổi model chỉ cần sửa `.env`, không phải sửa code (file 35 sẽ tận dụng điều này để tối ưu chi phí).
  - **Timeout và temperature cấu hình được** (`OPSDESK_LLM_TIMEOUT_S`, mặc định 30 giây): một lời gọi treo không được làm treo cả request của người dùng (file 26).
  - **Settings có kiểm tra** (pydantic-settings): thiếu key thì báo lỗi ngay lúc khởi động, thay vì đợi tới lần gọi đầu tiên mới hỏng.
  - **Ghi lại `usage`** vào trace và ledger chi phí (M07, M16), thay vì chỉ `print`.

## Hỏi thêm

**H: Không thấy chỗ nào truyền API key mà sao vẫn chạy được?**

Key được truyền **qua biến môi trường**, không qua tham số. Đường đi gồm 3 chặng:

1. `common.py`: `load_dotenv()` đọc file `.env` rồi chép từng dòng `TÊN=giá_trị` vào `os.environ` (các biến môi trường của tiến trình Python đang chạy). File 01 `import common` nên dòng này chạy trước mọi thứ.
2. `ChatOpenAI(model=...)`: khi không ai truyền `api_key=`, LangChain tự tìm `os.environ["OPENAI_API_KEY"]`.
3. Bên dưới LangChain là thư viện `openai`. Khi không ai truyền `base_url=`, nó tự tìm `os.environ["OPENAI_BASE_URL"]`. Nhờ vậy request đi tới gateway của khóa học chứ không tới api.openai.com.

Kiểm tra thật (không in giá trị key):
```
Trước load_dotenv: OPENAI_API_KEY có trong env? False
Sau load_dotenv:   OPENAI_API_KEY có trong env? True
ChatOpenAI tự lấy key?      True
openai_api_base trong LangChain: None           ← LangChain không giữ base_url...
base_url client openai dùng thật == .env? True  ← ...thư viện openai tự đọc từ env
```

**Vì sao làm vậy:** secret không bao giờ nằm trong code, nên commit code không làm lộ key (`.env` đã nằm trong `.gitignore`). Đổi gateway hay đổi key chỉ cần sửa `.env`. Cái giá: phép màu này "vô hình". Quên `load_dotenv()` là gặp lỗi `Missing credentials`, đúng lỗi bạn thấy ở lần chạy đầu khi chưa có `.env`. OpsDesk làm tường minh hơn: pydantic-settings đọc `.env` thành một object có kiểm tra, rồi truyền `api_key`/`base_url` rõ ràng vào client.
