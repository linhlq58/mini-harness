# 02 — Workflow deterministic

## 1. Ý chính
Trong workflow deterministic, **code quyết định các bước**, còn model chỉ làm một việc nhỏ, ở đây là gắn nhãn cho câu hỏi. Sau khi có nhãn, một `if/else` cố định (viết bằng code) chọn hàm xử lý. Model không được tự chọn làm gì tiếp theo.
Ví dụ đời thường: lễ tân bệnh viện chỉ hỏi "khám gì?" rồi chỉ sang đúng phòng. Quy trình trong từng phòng do bệnh viện quy định, lễ tân không tự ý chữa.

## 2. Mới so với file trước
- **Giữ nguyên:** `model = llm()`, cách gọi `model.invoke([SystemMessage(...), HumanMessage(...)])`.
- **Mới:**
  - Dòng 12–17: `LABELS` và `CLASSIFY_PROMPT`. Prompt giao cho model **một việc duy nhất** và ép định dạng đầu ra là "một từ".
  - Dòng 20–25: `classify()`, gồm lời gọi model và **kiểm tra nhãn bằng code**.
  - Dòng 28–44: ba hàm xử lý bằng Python thuần, **không gọi model**.
  - Dòng 47: `HANDLERS`, bảng "nhãn → hàm". Đây chính là `if/else` viết gọn thành dict.
  - Dòng 50–55: `run()`, chứa hai bước cố định: phân loại rồi rẽ nhánh.
  - Bắt đầu dùng `TICKETS` và `DOCS` từ `common.py`.
- **Bỏ:** phần lịch sử hội thoại của file 01. Mỗi câu hỏi được xử lý độc lập.

## 3. Đi qua code theo thứ tự chạy

**Bước 1: vòng lặp chạy 3 câu hỏi mẫu** (dòng 58–63). Mỗi câu đi qua `run()`.

**Bước 2: model phân loại** (dòng 22–25)
```python
reply = model.invoke([SystemMessage(CLASSIFY_PROMPT), HumanMessage(question)])
label = reply.content.strip().lower()
return label if label in LABELS else "other"
```
Model chỉ trả về một chuỗi chữ. Code làm sạch chuỗi đó (`strip`, `lower`) rồi **kiểm tra nó có nằm trong danh sách nhãn hợp lệ không**. Nếu model trả về thứ lạ, code dùng `other` làm phương án an toàn. Vì sao cần bước này: đầu ra của model là văn bản tự do, không có gì bảo đảm nó đúng định dạng. Code không được tin mù quáng.

**Bước 3: code rẽ nhánh** (dòng 54)
```python
answer = HANDLERS[label](question)
```
`HANDLERS[label]` lấy ra đúng hàm, `(question)` gọi hàm đó. Đây là lúc **code giữ quyền điều khiển**: cùng một nhãn thì luôn chạy cùng một hàm, theo cùng một cách.

**Bước 4: hàm xử lý chạy, không cần model**
- `handle_ticket` (dòng 28–33): dùng regex tìm mã `T-số` trong câu hỏi, rồi tra `TICKETS`.
- `handle_policy` (dòng 36–40): tìm tài liệu một cách rất thô, bằng từ cuối của tiêu đề. File 17 sẽ thay bằng RAG thật.
- `handle_other` (dòng 43–44): trả về một câu cố định.

## 4. Kết quả khi chạy
```
>>> Ticket T-1 của tôi sao rồi?
  model trả về: 'ticket'                                     ← Bước 2: model gắn nhãn
  nhãn dùng: ticket  ->  code gọi handle_ticket()            ← Bước 3: code chọn nhánh
  trả lời: T-1 'Laptop chậm' đang ở trạng thái: open.        ← Bước 4: tra dict, không cần model

>>> Chính sách mật khẩu là gì?
  model trả về: 'policy'
  nhãn dùng: policy  ->  code gọi handle_policy()
  trả lời: [Chính sách mật khẩu] Mật khẩu tối thiểu 12 ký tự, đổi mỗi 90 ngày, ...

>>> Hôm nay ăn trưa gì ngon?
  model trả về: 'other'
  nhãn dùng: other  ->  code gọi handle_other()
  trả lời: Mình chỉ hỗ trợ ticket và chính sách IT.
```
Mỗi câu chỉ có **một** lời gọi model, nên rẻ, nhanh và dễ dự đoán.

## 5. Phá thử

**A. Câu hỏi mơ hồ, mỗi câu chạy 3 lần**
```
>>> Laptop tôi chậm quá, làm sao giờ?          (cả 3 lần)
  model trả về: 'policy'
  trả lời: [Cấp laptop] Nhân viên mới nhận laptop trong 2 ngày làm việc; đổi máy sau 3 năm.

>>> T-2 lỗi VPN, hướng dẫn cài VPN thế nào?    (cả 3 lần)
  model trả về: 'policy'
  trả lời: [Hướng dẫn VPN] Cài FortiClient, đăng nhập bằng tài khoản công ty, ...
```
- Câu 1: model chọn `policy` và ổn định qua 3 lần chạy. Nhưng tài liệu trả về ("cấp laptop") **chẳng giúp gì** người đang bị máy chậm. Nhãn hợp lý, kết quả vẫn sai, vì không có nhánh nào dành cho "báo sự cố".
- Câu 2 hỏi **hai việc** (ticket T-2 và hướng dẫn VPN), nhưng workflow chỉ cho phép **một** nhãn, nên phần hỏi về ticket T-2 bị bỏ mất mà không ai hay.

**Ai chịu trách nhiệm cho lựa chọn đó?** Model chỉ đưa ra một gợi ý (cái nhãn). **Code và người viết code** chịu trách nhiệm: chính họ quyết định chỉ có 3 nhãn, mỗi câu chỉ được một nhãn, và nhãn `policy` thì dẫn tới hàm nào. Muốn sửa thì sửa thiết kế, ví dụ thêm nhãn `incident`, hoặc cho phép nhiều nhãn như router ở file 08.

**B. Bỏ câu "Chỉ trả về đúng một từ", thay bằng "Trả lời bằng một câu đầy đủ, nêu nhãn và lý do"**
```
>>> Ticket T-1 của tôi sao rồi?
  model trả về: 'Nhãn: ticket, vì bạn đang hỏi về tình trạng ticket hỗ trợ T-1 của mình.'
  nhãn dùng: other  ->  code gọi handle_other()
  trả lời: Mình chỉ hỗ trợ ticket và chính sách IT.
```
Model hiểu đúng ý (chữ "ticket" nằm ngay trong câu trả lời), nhưng sai định dạng. Lớp kiểm tra ở dòng 25 không nhận ra nhãn nên rơi về `other`. Chương trình **không crash** (an toàn), nhưng người dùng nhận câu trả lời sai. (Chỉ xóa câu "một từ" mà không thêm yêu cầu khác thì model vẫn trả về một từ, vì prompt vẫn liệt kê sẵn 3 nhãn.)

**Điều này chứng minh:** trong workflow, độ đúng của cả hệ thống phụ thuộc vào **thiết kế các nhánh** và **hợp đồng định dạng** giữa model với code. So khớp chuỗi văn bản là một hợp đồng mong manh. File 08 sẽ dùng *structured output* để model buộc phải trả về đúng kiểu dữ liệu.

## 6. Tự kiểm tra
**Câu hỏi:** Khi nào nên để code quyết định thay vì model?

<details><summary>Đáp án</summary>

Khi các bước **đã biết trước và ít thay đổi**, và khi bạn cần: (1) **dự đoán được**, cùng đầu vào cho cùng đường đi, dễ test và dễ eval (file 29); (2) **kiểm soát**, ví dụ thao tác có hậu quả như đóng ticket hay cấp quyền phải đi đúng quy trình duyệt (file 22, 25); (3) **rẻ và nhanh**, mỗi câu chỉ một lời gọi model nhỏ. Chỉ để model tự quyết (agent, file 03) khi số bước và thứ tự bước **không đoán trước được**. Quy tắc chung: dùng mức tự chủ thấp nhất mà vẫn đủ làm xong việc.
</details>

**Câu hỏi thêm:** Vì sao `handle_ticket` không gọi model?

<details><summary>Đáp án</summary>

Vì việc đó **không cần trí thông minh**: tìm mã T-số rồi tra dict là việc code làm đúng 100%, tức thì và miễn phí. Gọi model ở đây chỉ thêm chi phí, độ trễ và rủi ro model bịa ra trạng thái.
</details>

## 7. Nối sang OpsDesk
- **Ở đâu:** **M05** (router phân loại ý định rồi chuyển cho specialist) và **M14a** (workflow có bước duyệt, ví dụ đóng ticket hay cấp quyền chạy theo các bước cố định bằng LangGraph).
- **OpsDesk bọc thêm gì và vì sao:**
  - **Structured output** (Pydantic model) thay cho so khớp chuỗi, để có hợp đồng định dạng chắc chắn (sẽ học ở file 08).
  - **Nhiều ý định trong một câu**, chạy song song (file 08), vì người dùng thật hay hỏi gộp như câu 2 ở phần phá thử.
  - **Fallback có ghi log và event** khi route lỗi, thay vì âm thầm rơi về `other`, để biết hệ thống đoán sai bao nhiêu lần (M07).
  - Workflow viết bằng **LangGraph** (file 19) để có checkpoint, interrupt chờ người duyệt, và trace từng node.
